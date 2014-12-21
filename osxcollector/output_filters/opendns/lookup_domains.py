#!/usr/bin/env python

# -*- coding: utf-8 -*-
#
# LookupDomainsFilter uses OpenDNS to lookup the values in 'osxcollector_domains' and add 'osxcollector_opendns' key.
#
from osxcollector.output_filters.base_filters.output_filter import run_filter
from osxcollector.output_filters.base_filters. \
    threat_feed import ThreatFeedFilter
from osxcollector.output_filters.find_blacklisted import create_blacklist
from osxcollector.output_filters.opendns.api import InvestigateApi


class LookupDomainsFilter(ThreatFeedFilter):

    """Uses OpenDNS to lookup the values in 'osxcollector_domains' and add 'osxcollector_opendns' key."""

    def __init__(self, lookup_when=None, suspicious_when=None):
        super(LookupDomainsFilter, self).__init__('osxcollector_domains', 'osxcollector_opendns',
                                                  lookup_when=lookup_when, suspicious_when=suspicious_when, api_key='opendns')
        self._whitelist = create_blacklist(self.config.get_config('domain_whitelist'))

    def _lookup_iocs(self):
        """Caches the OpenDNS info for a set of domains.

        Domains on a whitelist will be ignored.
        """
        investigate = InvestigateApi(self._api_key)

        categorized_responses = investigate.categorization(list(self._all_iocs))
        for domain in categorized_responses.keys():
            if self._whitelist.match_values(domain) or not self._should_get_security_info(domain, categorized_responses[domain]):
                del categorized_responses[domain]

        security_responses = investigate.security(categorized_responses.keys())
        for domain in security_responses.keys():
            if self._should_store_ioc_info(categorized_responses[domain], security_responses[domain]):
                self._threat_info_by_iocs[domain] = {
                    'domain': domain,
                    'categorization': categorized_responses[domain],
                    'security': security_responses[domain],
                    'link': 'https://investigate.opendns.com/domain-view/name/{0}/view'.format(domain)
                }

    def _should_get_security_info(self, domain, categorized_info):
        """Figure out whether the info on the domain is interesting enough to gather more data.

        If the domain is already suspicious, get security info.
        If the domain isn't categorized, get security info.
        If the domain is related to suspicious_iocs, get security info.

        Args:
            domain - A string domain
            categorized_info - A dict of info returned by the OpenDNS categorization call
        Returns:
            boolean
        """
        if categorized_info['is_suspicious']:
            return True
        if (0 == categorized_info['status'] and
                0 == len(categorized_info.get('content_categories', [])) and
                0 == len(categorized_info.get('security_categories', []))):
            return True
        if domain in self._suspicious_iocs:
            return True
        return False

    def _should_store_ioc_info(self, categorized_info, security):
        """Figure out whether the data gathered is interesting enough to store in the output.

        Args:
            categorized_info - A dict of info returned by the OpenDNS categorization call
            security - A dict of info returned by the OpenDNS security call
        Returns:
            boolean
        """
        return categorized_info['is_suspicious'] or security['is_suspicious']


def main():
    run_filter(LookupDomainsFilter())


if __name__ == "__main__":
    main()