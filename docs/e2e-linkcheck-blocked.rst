:orphan:

######################################
E2E fixture: bot-blocked link recheck
######################################

.. warning::

   TEMPORARY (DM-55471). This page exists only to give the link-check
   service some URLs it will classify as ``blocked``, so that an
   end-to-end run exercises the local recheck and the contribution POST
   against the development Ook. Delete this file before merging.

Documenteer's own documentation happens to link to nothing that trips a
bot-protection edge — a recent check returned 165 ``ok`` and one
``failing`` URL, and no ``blocked`` ones — so the recheck-and-contribute
path never fires on it. The links below are Cloudflare-fronted publisher
sites that answer a datacenter IP with a ``403`` carrying
``cf-mitigated`` and ``server: cloudflare``, which is exactly what Ook
reads as ``blocked``.

The first three were verified to return that response even from a
residential address, so Ook's egress should certainly see it. The fourth
answers ``200`` from a residential address while still sitting behind
Cloudflare, which makes it the most likely of the set to be blocked at
Ook's GCP egress yet reachable from this Azure-hosted runner — the case
where the build clears the caveat and contributes a verified-OK result.

* `Monthly Notices of the Royal Astronomical Society <https://academic.oup.com/mnras>`__
* `AIP Publishing <https://pubs.aip.org>`__
* `Royal Society Publishing <https://royalsocietypublishing.org>`__
* `Cambridge Core <https://www.cambridge.org/core>`__
