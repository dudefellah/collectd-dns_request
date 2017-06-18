import collectd

import dns.resolver

import ipaddress

import socket
import signal
import sys

import time

PLUGIN_NAME = "dns_request"
DEFAULT_TIMEOUT = 5

Interval = 60

Queries = {}
Nameserver_Cache = {}


def _restore_sigchld():
    """
    Restore SIGCHLD handler for python <= v2.6
    It will BREAK exec plugin!!!
    See https://github.com/deniszh/collectd-iostat-python/issues/2 for details
    """
    if sys.version_info[0] == 2 and sys.version_info[1] <= 6:
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)


def dns_request_init():
    _restore_sigchld()


def dns_request_conf(config=None):
    """Collectd Plugin Configuration Parsing"""
    global Queries, Nameserver_Cache

    collectd.debug("config: {}".format(str(config.key)))
    Queries = {}
    for request in config.children:
        collectd.debug("C: {} = {}".format(request.key, request.values[0]))
        request_name = request.values[0]
        Queries[request_name] = {'recordtype': 'A', 'timeout': DEFAULT_TIMEOUT}
        for c in [x for x in request.children
                  if x.key.lower() in
                  ('query', 'server', 'timeout', 'sourceip', 'sourceport')
                  ]:
            collectd.debug("Queries[{}][{}] values: {}".format(
                request_name, c.key.lower(), c.values[0]))
            Queries[request_name][c.key.lower()] = c.values[0]

    collectd.debug("QUERIES: {}".format(Queries.keys()))
    required_args = set(['query', 'server', 'timeout'])
    for q, query in Queries.items():
        query = Queries[q]

        actual_args = set(sorted(query.keys()))

        if (not required_args.issubset(actual_args)):
            #        if (('query', 'server', 'timeout') not in query.keys()):
            collectd.warning("Request '{}' is missing either a Query, "
                             "Server or Timeout value ({}). Skipping.".format(
                                 q, query
                             ))
            query['skip'] = True

        if (('server' in query.keys()) and query['server'] not in Nameserver_Cache.keys()):
            try:
                resolver = dns.resolver.Resolver()
                results = resolver.query(query['server'], 'A')
                collectd.debug("RESULTS {}: {}".format(
                    query['server'], results))
                if results:
                    Nameserver_Cache[query['server']] = str(results[0])
            except dns.resolver.NXDOMAIN as e:
                collectd.warning("Unable to determine the IP of the server "
                                 "'{}', supplied in request '{}'".format(
                                     query['server'], q
                                 ))
                query['skip'] = True

        # Validate the SourceIP to see that it makes sense
        # (it's an IP and we can bind to it)
        if ('sourceip' in query.keys()):
            try:
                ip_addr = ipaddress.ip_address(unicode(query['sourceip']))
                if (type(ip_addr) is ipaddress.IPv6Address):
                    test_sock = socket.socket(socket.AF_INET6)
                    test_sock.bind(('', 0))
                elif (type(ip_addr) is ipaddress.IPv4Address):
                    test_sock = socket.socket(socket.AF_INET)
                    test_sock.bind(('', 0))
                else:
                    raise ValueError("'{}' isn't an IPv4 or IPv6 address"
                                     "!?".format(query['sourceip']))
                    query['skip'] = True
            except ValueError as v:
                collectd.error("Source IP in '{}' ({}) doens't look valid!"
                               " {}".format(q, query['sourceip'], v)
                               )
                query['skip'] = True

        # Validate the SourcePort to see that it makes sense:
        # It's in a good range and we can bind to it.
        # Binding's a little redundant, but it'll complain if we don't
        # have permission, or if the port's already in use, where checking the
        # range will only tell us if the port is a reasonable number
        if ('sourceport' in query.keys()):
            source_port = int(query['sourceport'])
            if (source_port < 0 or source_port > 65535):
                query['skip'] = True
                collectd.warning("Invalid source port '{:d}' provided. Skipping "
                                 "the DNS query for '{}' [{}]".format(
                                     source_port, query['query'],
                                     query['recordtype']
                                 ))

            else:
                test_sock = socket.socket(socket.AF_INET)
                test_sock.bind(('', source_port))
                test_sock.close()

    collectd.debug("QUERIES: {}".format(Queries))


def dns_request_read(data=None):
    global Queries, Nameserver_Cache
    query_values = []
    collectd.debug("NAMSERVER CACHE: {}".format(Nameserver_Cache))
    for (q, query) in Queries.items():
        if ('skip' in query.keys() and query['skip']):
            continue

        collectd.debug("Q: {}".format(query))

        resolver = dns.resolver.Resolver()
        resolver.timeout = float(query['timeout'])
        resolver.lifetime = float(resolver.timeout + 1)
        server_ip = None

        source_ip = None
        source_port = 0

        # Grab the nameserver's IP
        if 'server' in query.keys():
            # We've already checked this stuff, so we _should_ be guaranteed
            # a valid nameserver in here. If there isn't, it'd be best
            # for it to die as loudly as possible (ie without us handling it)
            resolver.nameservers = [Nameserver_Cache[query['server']]]

        if ('sourceip' in query.keys()):
            source_ip = query['sourceip']

        if ('sourceport' in query.keys()):
            source_port = int(query['sourceport'])

        collectd.debug("nameservers: {}".format(resolver.nameservers))
        collectd.debug("resolver.query({}, {})".format(
            query['query'], query['recordtype']))
        result = []
        response_time = -1
        try:
            start = time.time()
            result = resolver.query(query['query'], query[
                'recordtype'], tcp=False, source=source_ip,
                source_port=source_port)
            end = time.time()
            if (result):
                response_time = float(end - start)
        except dns.resolver.NoAnswer as e:
            # We can supply raise_on_no_answer=False to resolver.query (above)
            # in order to avoid doing this whole try block, but this
            # works so I'll keep it for now
            collectd.debug("No answer from {} for {} [{}]".format(
                resolver.nameservers, query['query'], query['recordtype']))
        except dns.resolver.Timeout as e:
            collectd.debug("Request timed out from {} for {} [{}]".format(
                resolver.nameservers, query['query'], query['recordtype']))

        val = collectd.Values(
            plugin=PLUGIN_NAME,
            plugin_instance=query['query'],
            type='response_time',
            type_instance=query['recordtype'],
            values=[response_time]
        )
        collectd.debug("Response time: {}".format(response_time))
        collectd.debug("Result: {}".format(result))
        query_values.append(val)

    for val in query_values:
        collectd.debug("Dispatching {}".format(val))
        val.dispatch()


if __name__ != '__main__':
    collectd.register_init(dns_request_init)
    collectd.register_config(dns_request_conf)
    collectd.register_read(dns_request_read, Interval)
else:
    # Add some testing in at some point? Collectd plugins don't seem
    # to be very test-friendly
    pass
