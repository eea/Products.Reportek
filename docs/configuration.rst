Configuration
=============

Error monitoring
----------------
Reportek can send error events to Sentry_. For this, a ``DSN`` needs to
be configured in the environment::

    [zope-instance]
    recipe = plone.recipe.zope2instance
    # ...
    eggs =
        # ... required eggs ...
        raven
    environment-vars =
        # ... other environment vars ...
        REPORTEK_ERROR_SENTRY_URL <THE_DSN>

.. _sentry: http://sentry.readthedocs.org/


Cron jobs
---------
A cron job must be set up to check for automatic QA results. It should
perform a GET request on the URL
``/ReportekEngine/runAutomaticApplications?p_applications=AutomaticQA``
once every few minutes.
