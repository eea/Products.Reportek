

# Working with envelopes using the JSON API
In order to provide the possibility of machine-to-machine interaction with the envelopes, an API has been implemented. This document provides examples for a rather typical workflow of an envelope's lifecycle. We will be using curl for the examples below as it is pretty self explanatory and they can easily be adapted for whatever library you are using. The examples are using https://cdrtest.eionet.europa.eu deployment.

## Creating an envelope

The first step would be to create the envelope. This can be achieved with the following curl request:

```bash
 curl -v -u "user:password" -H "Accept: application/json" -X POST \
 -L -d "title=test_api1&descr=''&year=2019&endyear=''&partofyear=WHOLE_YEAR&locality=''"\ 
 "https://cdrtest.eionet.europa.eu/ro/colwydrga/manage_addEnvelope"
```
We're basically passing some required query parameters to the manage_addEnvelope endpoint of a Collection. Most of the parameters are self explanatory, but the _partofyear_ can have the following values:
* WHOLE_YEAR
* FIRST_HALF
* SECOND_HALF
* FIRST_QUARTER
* SECOND_QUARTER
* THIRD_QUARTER
* FOURTH_QUARTER

The result for this request is:
```json
{
  "errors": [], 
  "envelopes": [
      {
          "periodEndYear": "", 
          "description": "''", 
          "countryCode": "RO", 
          "obligations": [
              "673"
          ], 
          "modifiedDate": "2019-11-22T10:44:03Z", 
          "periodDescription": "Whole Year", 
          "isReleased": 0, 
          "periodStartYear": 2019, 
          "title": "test_api1", 
          "url": "https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w", 
          "reportingDate": "2019-11-22T10:44:03Z"
      }
  ]
}
```
In the response, we have a JSON object with relevant metadata for the newly created envelope. Depending on the deployment type and the workflow, there can be additional properties in that envelope response, like _companyName_ and _companyId_.

An envelope's lifecycle is dictated by the associated workflow. The workflow is mapped to the obligation of the envelope. In the above example, the obligation is 673, this is not passed as a query parameter, but it's instead inherited from the parent Collection.

A workflow can have multiple steps or activities (in this document we're going to call them activities). Many Reportnet workflows use a common _Draft_ activity as the first step of a workflow. Each activity have an associated application and while these are outside the scope of this document, it's important to keep in mind that some activities require the reporter's input, while others are automatic and require no intervention from the reporter.

## Activating a workitem
Each new workflow activity that the envelope transitions into will result in the creation of a _workitem_ object inside the envelope object. They are created automatically and serve as a history of an envelope with relevant metadata stored in it's attributes.

The _Draft_ activity is a manual activity and requires an action from the reporter. The typical interaction with the portal, requires the user to activate the _Draft_ activity first, then upload or use a webform to generate files inside the envelope. In order to activate the _Draft_ activity using curl, we can issue the following request:

```bash
curl -v -u "user:password" -H "Accept: application/json" -L -d "workitem_id=0&DestinationURL=https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w" "https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w/activateWorkitem"
```

In this particular example, the workflow mapped to the envelope has the _Draft_ activity as it's first activity, therefore, we know that it's first workitem has an id of 0 (the id's are incremental, starting from 0). The _DestinationURL_ has the newly created envelope's url as it's value.

The output for this request is:
```json
{
    "workitem": {
        "url": "https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w/0", 
        "status": "active", 
        "id": "0", 
        "actor": "user"
    }
}
```

Notice that the status of the workitem is now 'active', meaning, we can safely interact with the Draft activity. A workitem can have one of the following statuses:

* blocked
* inactive
* active
* suspended
* fallout
* complete

In order to inactivate this activity, so that a reporter can normally take over and interact with the envelope, you can use the following curl request:
```bash
curl -v -H "Accept: application/json" -v -u "user:password" -L "https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w/inactivateWorkitem?workitem_id=0&DestinationURL=https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w" 
```

The output for this request is:
```json
{
    "workitem": {
        "url": "https://cdrtest.eionet.europa.eu/ro/colwsyg9g/envxxzquw/0", 
        "status": "inactive", 
        "id": "0", 
        "actor": "" 
    }
}
```
## Uploading a file
Once the _Draft_ activity is activated, you can upload a file inside the envelope. The default upload endpoint is _manage_addDocument_, this just uploads the file as is, without making any changes or conversions to it. Some workflows use other upload endpoints which will be described later. For file upload, only the file and id are mandatory, but for this request, I've also added the title and set it to be restricted from public:
```bash
curl -X POST -v -H "Accept: application/json" -u "user:password" -F "file=@/path/to/test.xml" -F "id=test.xml" -F "title=title" -F "restricted=true" -L "https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w/manage_addDocument"
```

The output of this request can be seen below:
```json
{
    "files": [
        {
            "fileSizeHR": "228 MB", 
            "contentType": "text/xml", 
            "uploadDate": "2019-11-27T13:35:16Z", 
            "title": "title", 
            "url": "https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w/test.xml", 
            "isRestricted": 1, 
            "schemaURL": "http://dd.eionet.europa.eu/schemas/id2011850eu-1.0/AirQualityReporting.xsd", 
            "fileSize": 238610026
        }
    ], 
    "errors": []
}
```

Some workflows require different type of conversions for the uploaded file. The other upload endpoints are:
* *convert_excel_file* (Converts Data Dictionary template filled files .XLS or .ODS into .XML)
* *manage_addDocOrZip* (Adds a file or unpacks a zip in the envelope. If the file is XML, it calls replace_dd_xml, otherwise, it just uploads the file using manage_addDocument)
* *manage_addDDFile* (Adds a file created using a DD template as follows:
>     - if the file is a spreadsheet, it calls convert_excel_file
>     - if the file XML, it calls replace_dd_xml
>     - if the file zip, it calls manage_addDDzipfile
>     - otherwise it calls manage_addDocument)
* *manage_addDDzipfile* (Expands a zipfile into a number of Documents.
                         For the XML files, checks if the schema is correct for that dataflow, meaning the schema is part of the 'required_schema' list of approved schemas. It uploads all files, then deletes the files that should have not been uploaded because of the wrong schema.)
* *uploadGISfiles* (Uploads GIS files)
* *uploadGISZIPfiles* (Uploads zipped GIS files)
* *manage_addMMRXLSFile* (Adds an XLS file based on the MMR template and converts it to XML)

## Forwarding an envelope
After the file is uploaded, we have to forward the envelope. Most workflows transition to the AutomaticQA activity and usually, there's at least one more activity before the AutomaticQA which cleans other AutomaticQA feedback files.

Forwarding the envelope:
```bash
curl -v -H "Accept: application/json" -u "user:password" -L -d "workitem_id=0&release_and_finish=0" "https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w/completeWorkitem"
```

output:
```json
{
    "workitem": {
        "url": "https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w/0", 
        "status": "complete", 
        "id": "0", 
        "actor": "user"
    }
}
```

We're forwarding from the Draft application, so we're passing the workitem_id 0. Alongside, there's the _release_and_finish_ parameter. This parameter, helps to determine which workflow transition is to be taken. The transition conditions are defined on a workflow level.

The AutomaticQA process can be a time consuming task, therefore, in order to check the status of the AutomaticQA process, we could use the following:
```bash
curl -v -H "Accept: application/json" -v -u "user:password" -L "https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w/get_current_workitem"
```

This will return the current workitem, which as explained above is mapped to the current activity.
The output is something similar to:
```json
{
    "workitem": {
        "status": "complete", 
        "activeTime": 59.28832197189331, 
        "url": "https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w/14", 
        "actor": "openflow_engine", 
        "activityId": "AutomaticQA", 
        "id": "14"
    }
}
```
Another option would be to use the envelopes API and check it's full history, like so:
```bash
curl "https://cdrtest.eionet.europa.eu/api/envelopes?url=https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w&fields=history"
```

For this particular case, I will be showing a more complex envelope lifecycle output:
```json
{
    "errors": [], 
    "envelopes": [
        {
            "history": [
                {
                    "activity_id": "Draft", 
                    "activity_status": "complete", 
                    "blocker": false, 
                    "title": "Draft by robaaoli", 
                    "modified": "2019-11-22T12:23:20Z", 
                    "id": "0"
                }, 
                {
                    "activity_id": "DeleteAutomaticQAFeedback", 
                    "activity_status": "complete", 
                    "blocker": false, 
                    "title": "DeleteAutomaticQAFeedback by openflow_engine", 
                    "modified": "2019-11-22T12:23:20Z", 
                    "id": "1"
                }, 
                {
                    "activity_id": "AutomaticQA", 
                    "activity_status": "complete", 
                    "blocker": false, 
                    "title": "AutomaticQA by openflow_engine", 
                    "modified": "2019-11-22T12:24:01Z", 
                    "id": "2"
                }, 
                {
                    "activity_id": "Draft", 
                    "activity_status": "complete", 
                    "blocker": false, 
                    "title": "Draft by robaaoli", 
                    "modified": "2019-11-22T12:38:07Z", 
                    "id": "3"
                }, 
                {
                    "activity_id": "DeleteAutomaticQAFeedback", 
                    "activity_status": "complete", 
                    "blocker": false, 
                    "title": "DeleteAutomaticQAFeedback by openflow_engine", 
                    "modified": "2019-11-22T12:38:07Z", 
                    "id": "4"
                }, 
                {
                    "activity_id": "AutomaticQA", 
                    "activity_status": "complete", 
                    "blocker": false, 
                    "title": "AutomaticQA by openflow_engine", 
                    "modified": "2019-11-22T12:39:01Z", 
                    "id": "5"
                }, 
                {
                    "activity_id": "Draft", 
                    "activity_status": "complete", 
                    "blocker": false, 
                    "title": "Draft by robaaoli", 
                    "modified": "2019-11-22T12:52:01Z", 
                    "id": "6"
                }, 
                {
                    "activity_id": "DeleteAutomaticQAFeedback", 
                    "activity_status": "complete", 
                    "blocker": false, 
                    "title": "DeleteAutomaticQAFeedback by openflow_engine", 
                    "modified": "2019-11-22T12:52:01Z", 
                    "id": "7"
                }, 
                {
                    "activity_id": "AutomaticQA", 
                    "activity_status": "complete", 
                    "blocker": true, 
                    "title": "AutomaticQA by openflow_engine", 
                    "modified": "2019-11-22T12:59:01Z", 
                    "id": "8"
                }, 
                {
                    "activity_id": "Draft", 
                    "activity_status": "active", 
                    "blocker": false, 
                    "title": "Draft by niikkpek", 
                    "modified": "2019-11-22T14:13:40Z", 
                    "id": "9"
                }
            ]
        }
    ]
}
```

The workitem_id's correspond with the history steps. In the case above, in order to see if the AutomaticQA process has finished, we need to look at the last AutomaticQA history step, with id="8"(this is also the workitem_id). If the activity_status is "active", this means that the AutomaticQA process is still running, while a value of "complete", indicates that the AutomaticQA process has been completed.

After the AutomaticQA process is completed, the list of feedbacks can be retrieved by interrogating the API:
```bash
curl "https://cdrtest.eionet.europa.eu/api/envelopes?url=https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w&fields=feedbacks"
```

This returns the following:
```json
{
    "errors": [], 
    "envelopes": [
        {
            "feedbacks": [
                {
                    "activityId": "AutomaticQA", 
                    "contentType": "text/html;charset=UTF-8", 
                    "feedbackStatus": "INFO", 
                    "title": "AutomaticQA result for file test.xml: XML Schema validation", 
                    "url": "https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w/AutomaticQA_47976", 
                    "automatic": 1, 
                    "postingDate": "2019-11-22T12:54:01Z", 
                    "documentId": "test.xml", 
                    "feedbackMessage": "XML Schema validation passed without errors."
                }, 
                {
                    "activityId": "AutomaticQA", 
                    "contentType": "text/html", 
                    "feedbackStatus": "BLOCKER", 
                    "title": "AutomaticQA result for file test.xml: Check AQR obligations", 
                    "url": "https://cdrtest.eionet.europa.eu/ro/colwydrga/envxde78w/AutomaticQA_47977", 
                    "automatic": 1, 
                    "postingDate": "2019-11-22T12:59:01Z", 
                    "documentId": "test.xml", 
                    "feedbackMessage": "This XML file did NOT pass the following BLOCKER check(s): E02,E06,E11,E12,E25,E26"
                }
            ]
        }
    ]
}
```


Note that workitem_id, is the id of the object mapped to a specific workflow activity for that specific envelope. release_and_finish parameter used for forwarding the envelope is strictly dependent on the workflow. Based on this parameter, an envelope can go to one state or another.

Keep in mind that, depending on the workflow and envelope, that the current state is the last history entry, but there can be more than one Draft instance, for example, each with it's own workitem_id.
