# DNS Requester Plugin for Collectd

This plugin was created to make it easy to ensure that a local (authoritative)
DNS server is responding to requests in an appropriate amount of time. Since
all the plugin does is report on the amount of time a DNS request took, this
could be used for any DNS response time tracking need. For example, it could
be quite useful if you're trying to see how DNS latency is affecting overall
network latency.

DNS requests are made using the _dns.resolver_ module from (dnspython)[http://www.dnspython.org].
You should be able to recognize some of the "request" options in the
configuration section as arguments you can pass along to _dns.resolver_'s
**query** function, so if you want a little more information on how they're
used, please check the **dnspython** documentation.

# Installation

You can use setup.py (setuptools) to install the plugin automatically.

If you'd like to do it manually, this plugin should be as easy to install
as any other plugin for collectd. Simply add _dns_request.py_ to your plugin
path. Collectd looks at **sys.path** in order to find any Python plugins,
and you can add additional search paths for your plugin with the
**ModulePath** keyword in the [Python section](https://collectd.org/documentation/manpages/collectd-python.5.shtml)
of collectd.conf.

# Configuration

```
<Plugin "python">
...

    Import "dns_request"
    <Module "dns_request">
        <Request "request_title">
            Query "google.ca"
            Server "8.8.8.8"    # Optional: Default is whatever is in /etc/resolv.conf
            Timeout 10          # Optional: Default 5 seconds
            SourceIP "1.2.3.4"  # Optional: Server default IP
            SourcePort 123456   # Optional: Default is "0" (automatic local port selection)
        </Request>
    </Module>
</Plugin>
```

#
