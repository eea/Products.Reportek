Configuration
=============

Error emails
------------
Reportek can send alert emails to administrators when an error occurs.
It uses the Zope2 SiteErrorLog mechanism, so if an exception is ignored
in ``error_log``, then no alert is sent.

* Make sure `Copy exceptions to the event log` is enabled in the
  top-level ``error_log`` object.

* Set up an SMTP server and list of administrator emails, either in
  `zope.conf` or, as shown below, in `buildout.cfg`::

    [zope-instance]
    recipe = plone.recipe.zope2instance
    #....
    environment-vars =
        REPORTEK_ERROR_MAIL_TO admin@example.com
        REPORTEK_ERROR_SMTP_HOST smtp.example.com
