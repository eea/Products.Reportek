# Envelopes


## Version: 1.0.0

### /envelopes

#### GET
##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ---- |
| isReleased | query | Released(1) or Unreleased(0) envelopes to return | No | integer |
| url | query | Url of the envelopes or part of to return | No | string |
| countryCode | query | Country code in ISO "ALPHA-2 Code format for envelopes to return | No | [ string ] |
| reportingDate | query | Return envelopes with this reporting date. Please note that the reporting date is the creation date for unreleased envelopes. | No | date |
| reportingDateStart | query | Return envelopes that have a reporting date in range of reportingDateStart and reportingDateEnd or today if reportingDateEnd is missing. | No | date |
| reportingDateEnd | query | Return envelopes that have a reporting date in range of reportingDateStart and reportingDateEnd. If reportingDateStart is missing, all envelopes with reporting date <= reportingDateEnd will be returned. | No | date |
| obligations | query | Return envelopes with one of the following obligations | No | [ integer ] |
| periodDescription | query | Return envelopes with specified periodDescription | No | [ string ] |
| modifiedDate | query | Return envelopes with specified modifiedDate. date format. | No | date |
| modifiedDateStart | query | Return envelopes that have a modified date in range of modifiedDateStart and modifiedDateEnd or today if modifiedDateEnd is missing. | No | date |
| modifiedDateEnd | query | Return envelopes that have a modified date in range of modifiedDateStart and modifiedDateEnd or today if modifiedDateStart is missing. | No | date |
| status | query | Return envelopes that have the following status - deprecated, please use activity instead | No | [ string ] |
| statusDate | query | Return envelopes that have a status with the following statusDate. - deprecated, please use activityDate instead | No | date |
| statusDateStart | query | Return envelopes that have a status date in range of statusDateStart and statusDateEnd or today if statusDateEnd is missing. - deprecated, please use activityDateStart instead | No | date |
| statusDateEnd | query | Return envelopes that have a status date in range of statusDateStart and statusDateEnd or today if statusDateStart is missing. - deprecated, please use activityDateEnd instead | No | date |
| activity | query | Return envelopes that have the following activity | No | [ string ] |
| activityDate | query | Return envelopes that have an activity with the following activityDate. | No | date |
| activityDateStart | query | Return envelopes that have an activity date in range of activityDateStart and activityDateEnd or today if activityDateEnd is missing. | No | date |
| activityDateEnd | query | Return envelopes that have an activity date in range of activityDateStart and activityDateEnd or today if activityDateStart is missing. | No | date |
| activityStatus | query | Return envelopes with activity status of. | No | [ string ] |
| fields | query | Return envelopes with only the fields specified | No | [ string ] |

##### Responses

| Code | Description | Schema |
| ---- | ----------- | ------ |
| 200 | List released or unreleased envelopes | object |

### Models


#### Envelope

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| title | string | The envelope's title. | No |
| description | string | The envelope's description. | No |
| obligations | [ integer ] | The obligations for which the envelope has been created. | No |
| periodStartYear | string | The starting year of the period for which the envelope has been created. | No |
| periodEndYear | string | The ending year of the period for which the envelope has been created. | No |
| countryCode | string | The envelope's country code (ISO Alpha-2). | No |
| reportingDate | string (dateTime) | The envelope's reporting date. Please note that the reporting date is the creation date for unreleased envelopes. | No |
| reportingDateStart | string (dateTime) | Return envelopes that have a reporting date in range of reportingDateStart and reportingDateEnd or today if reportingDateEnd is missing. | No |
| reportingDateEnd | string | Return envelopes that have a reporting date in range of reportingDateStart and reportingDateEnd. If reportingDateStart is missing, all envelopes with reporting date <= reportingDateEnd will be returned. | No |
| url | string | The envelope's URL. | No |
| modifiedDate | string (dateTime) | The envelope's modification date. Please note that there are many potential events/actions that can alter the modificationDate of an envelope | No |
| modifiedDateStart | string (dateTime) | Return envelopes that have a modified date in range of modifiedDateStart and modifiedDateEnd or today if modifiedDateEnd is missing. | No |
| modifiedDateEnd | string (dateTime) | Return envelopes that have a modified date in range of modifiedDateStart and modifiedDateEnd or today if modifiedDateStart is missing. | No |
| periodDescription | [PeriodDescription](#perioddescription) |  | No |
| isReleased | integer | The envelope's release status | No |
| isBlockedByQCError | integer | Is the envelope blocked by a QC Error. | No |
| status | string | The workflow status of the envelope - deprecated, please use activity instead. | No |
| statusDate | string (dateTime) | The date the workflow status has been set. - deprecated, please use activityDate instead. | No |
| activity | string | The workflow activity of the envelope. | No |
| activityDate | string (dateTime) | The date the workflow activity has been set. | No |
| activityStatus | string | The status of the activity | No |
| creator | string | The envelope's creator. | No |
| hasUnknownQC | integer | Is there an AutomaticQA feedback with no valid feedback status | No |
| files | [ [File](#file) ] | The list of files attached to the envelope. | No |
| history | [ [History](#history) ] | The workflow history of the envelope. | No |
| companyId | string | The company ID associated with the envelope's parent Collection | No |
| companyName | string | The company name associated with the envelope's parent Collection | No |

#### File

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| contentType | string | The file's content type. The file's content type is determined by file extension, request headers and then falling back to Zope's content type guessing algorithm | No |
| title | string | The file's title. | No |
| url | string | The file's URL. | No |
| uploadDate | string (dateTime) | The file's upload date. | No |
| schemaURL | string | The URL of the file's schema. | No |
| fileSize | integer | The size of the file in bytes | No |
| fileSizeHR | string | The size of the file in human readable format. | No |
| hash | string | The file's sha256 hash | No |
| archivedFiles | [ string ] | The list of files that have been archived. Available only if there is an archive attached to the envelope and if it can be opened. | No |
| isRestricted | integer | The document's restricted status | No |

#### Feedback

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| contentType | string | The feedback's content type. | No |
| title | string | The feedback's title. | No |
| url | string | The feedback's URL. | No |
| postingDate | string (dateTime) | The feedback's posting date. | No |
| documentId | string | The file to which the feedback refers to. | No |
| activityId | string | The activity which generated the automatic feedback | No |
| automatic | integer | Feedback type. | No |
| feedbackStatus | string | The feedback status. | No |
| feedbackMessage | string | The feedback message. | No |
| isRestricted | integer | The feedback's restricted status. | No |
| attachments | [ object ] | The list of feedback attachments. | No |

#### History

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| activity_id | string | The id of the activity/workflow. | No |
| activity_status | string | The status of the activity/workflow. | No |
| blocker | boolean | The blocker status of the activity/workflow. | No |
| title | string | The title of the activity/workflow. | No |
| modified | string (dateTime) | The modification date of the activity/workflow. | No |
| id | string | The id of the activity/workflow. | No |

#### Error

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| title | string | The error's title. | No |
| description | string | The error's description | No |

#### PeriodDescription

The envelope's reporting period description.

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| PeriodDescription | string | The envelope's reporting period description. |  |