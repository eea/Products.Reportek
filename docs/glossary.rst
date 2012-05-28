Glossary
========

.. glossary::

    Data Repository
        A website based on the Reportek product. Examples of such instances are:
        `Central Data Repository <http://cdr.eionet.europa.eu>`_ and
        `Mediterranean Data Repository <http://mdr.eionet.europa.eu>`_

    Collection
        Folder-like container used to create a Data Repository site structure
        per countries (localities) and :term:`reporting obligations
        <reporting obligation>`. As the last leaf, Collections contain
        :term:`Envelopes <envelope>`.

    Envelope
        Folder-like container that holds the files for one :term:`delivery
        <delivery>` in response to one or more :term:`reporting obligations
        <reporting obligation>` and for a certain period. Depending on the
        requirements of the reporting obligation, sometimes there
        will only be one file in the envelope and on other occasions there will be
        many. The envelope provides transparency and traceability for a particular
        delivery. It is the unit processed by the data handlers when merging
        national data into one data set.

        The activities done in an envelope by the different users succeed according
        to a predefined :term:`workflow <workflow>`, usually custom-designed to fit
        the needs of each reporting obligation.

    Release
        The action of making the content of an envelope publicly available. Based on
        the 'released' status of an envelope - boolean. When released, the Reporters are not
        working on their deliveries and the contents of the envelope is publicly
        available. When not released, the contents of an envelope are visible
        only to users having the role of Reporter, Client or Auditor.

    Delivery
        A collection of files uploaded by country Reporters in response to one
        or more :term:`reporting obligations <reporting obligation>`.

    Reporting obligation
       Requirements to provide information agreed between countries and
       international bodies such as the EEA or international conventions.
       Reporting obligations provide the basis for most environmental information
       flows. In a Data Repository, the list of reporting obligations is
       usually grabbed from a remote repository, such as `Eionet Reporting
       Obligation Database <http://rod.eionet.europa.eu>`_.

    Workflow
        The process consisting of activities (states) and transitions from one
        activity to another. Envelopes have one workflow associated to each of
        them; the process is assigned to an envelope at its creation time, based
        on the country and reporting obligation(s) of the envelope.

    Document
        File uploaded in an envelope, accompanied by metadata

    Feedback
        Item uploaded in an envelope, containing an evaluation of a single file or of
        the entire delivery. Feedback items are uploaded either manually, by Clients,
        or automatically, by the a service such as the :term:`Automatic QA`.

    Automatic QA
        An activity executed by the system - part of a typical envelope workflow. It
        sends all the XML files for which QA scripts are available to the QA service
        and places the result in the envelope as Feedback.

    Manual QA
        An activity triggered by a user (usually a Reporter who wants to check the
        quality of the data before submitting the delivery) who clicks on a 'Run QA'
        button displayed next to a file and sees the validation results in a
        temporary page. The remote QA service is called to retrieve the results.

    Converter
        Program that converts a file of a mime type into another format. Reportek uses
        local and remote converters. The local ones call programs from the local disk
        with the specified parameters. The remote ones use a conversion service, such
        as the `Eionet Conversion Service <http://converters.eionet.europa.eu>`_

    Dataflow
        Synonym to :term:`reporting obligation <reporting obligation>`
