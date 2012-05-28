Glossary
========

.. glossary::

    Collection
        Folder-like container used to create a Data Repository site structure 
        per countries (localities) and :term:`reporting obligations
        <reporting obligation>`. As the last leaf, Collections contain 
        :term:`Envelopes <envelope>`

    Envelope
        Folder-like container that holds a :term:`delivery
        <delivery>` for a country (locality), for a certain period and for 
        one or more reporting obligations. The activities done in an envelope 
        succeed according to a predefined :term:`workflow <workflow>`, usually
        different for each reporting obligation

    Release
        Status of an envelope - boolean. When released, the Data Reporters
        are not working on their deliveries and the content of the envelope
        is publicly available

    Delivery
        A collection of files uploaded by Data Reporters in response to one
        or more :term:`reporting obligations <reporting obligation>`

    Reporting obligation
       Requirements to provide information agreed between countries and 
       international bodies such as the EEA or international conventions.
       Reporting obligations provide the basis for most environmental information
       flows. In a Data Repository, the list of reporting obligations is
       usually grabbed from a remote repository, such as _Eionet Reporting
       Obligation Database: http://rod.eionet.europa.eu

    Workflow
        The process consisting of activities (states) and transitions from one
        activity to another. Envelopes have one workflow associated to each of
        them, computed at their creation time, based on the country and reporting
        obligation(s) of the envelope  

    Automatic QA
        .. todo:: describe this

    Converter
        .. todo:: describe this

    Dataflow
        .. todo:: describe this

