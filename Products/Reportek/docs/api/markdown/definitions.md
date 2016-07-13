
<a name="definitions"></a>
## Definitions

<a name="envelope"></a>
### Envelope

|Name|Description|Schema|
|---|---|---|
|**countryCode**  <br>*optional*|The envelope's country code (ISO Alpha-2).|string|
|**creator**  <br>*optional*|The envelope's creator.|string|
|**description**  <br>*optional*|The envelope's description.|string|
|**files**  <br>*optional*|The list of files attached to the envelope.|< [File](#file) > array|
|**history**  <br>*optional*|The workflow history of the envelope.|< [History](#history) > array|
|**isBlockedByQCError**  <br>*optional*|Is the envelope blocked by a QC Error.|integer|
|**isReleased**  <br>*optional*|The envelope's release status|integer|
|**modifiedDate**  <br>*optional*|The envelope's modification date.|string|
|**obligations**  <br>*optional*|The obligations for which the envelope has been created.|< integer > array|
|**periodDescription**  <br>*optional*||[PeriodDescription](#perioddescription)|
|**periodEndYear**  <br>*optional*|The ending year of the period for which the envelope has been created.|string|
|**periodStartYear**  <br>*optional*|The starting year of the period for which the envelope has been created.|string|
|**reportingDate**  <br>*optional*|The envelope's reporting date.|string|
|**status**  <br>*optional*|The workflow status of the envelope.|string|
|**statusDate**  <br>*optional*|The date the workflow status has been set.|string|
|**title**  <br>*optional*|The envelope's title.|string|
|**url**  <br>*optional*|The envelope's URL.|string|


<a name="error"></a>
### Error

|Name|Description|Schema|
|---|---|---|
|**description**  <br>*optional*|The error's description|string|
|**title**  <br>*optional*|The error's title.|string|


<a name="file"></a>
### File

|Name|Description|Schema|
|---|---|---|
|**archived_files**  <br>*optional*|The list of files that have been archived. Available only if there is an archive attached to the envelope and if it can be opened.|< string > array|
|**contentType**  <br>*optional*|The file's content type.|string|
|**schemaURL**  <br>*optional*|The URL of the file's schema.|string|
|**title**  <br>*optional*|The file's title.|string|
|**uploadDate**  <br>*optional*|The file's upload date.|string|
|**url**  <br>*optional*|The file's URL.|string|


<a name="history"></a>
### History

|Name|Description|Schema|
|---|---|---|
|**activity_id**  <br>*optional*|The id of the activity/workflow.|string|
|**activity_status**  <br>*optional*|The status of the activity/workflow.|string|
|**blocker**  <br>*optional*|The blocker status of the activity/workflow.|boolean|
|**id**  <br>*optional*|The id of the activity/workflow.|string|
|**modified**  <br>*optional*|The modification date of the activity/workflow.|string|
|**title**  <br>*optional*|The title of the activity/workflow.|string|


<a name="perioddescription"></a>
### PeriodDescription
The envelope's reporting period description.

*Type* : enum (Whole Year, First Half, Second Half, First Quarter, Second Quarter, Third Quarter, Fourth Quarter, January, February, March, April, May, June, July, August, September, October, November, December)



