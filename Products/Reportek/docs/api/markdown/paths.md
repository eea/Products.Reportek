
<a name="paths"></a>
## Resources

<a name="envelopes_resource"></a>
### Envelopes

<a name="envelopes-get"></a>
#### GET /envelopes

##### Parameters

|Type|Name|Description|Schema|Default|
|---|---|---|---|---|
|**Query**|**countryCode**  <br>*optional*|Country code in ISO "ALPHA-2 Code format for envelopes to return|enum (AL, DZ, AD, AM, AT, AZ, BY, BE, BA, BG, HR, CY, CZ, DK, EG, EE, EU, FI, FR, GE, DE, GI, GR, GL, HU, IS, IE, IL, IT, JO, KZ, XK, KG, LV, LB, LY, LI, LT, LU, MK, MT, MD, MC, ME, MA, NL, NO, PS, PL, PT, RO, RU, SM, RS, SK, SI, ES, SE, CH, SY, TJ, TN, TR, TM, UA, GB, UZ, VA)||
|**Query**|**fields**  <br>*optional*|Return envelopes with only the fields specified|< enum (files, url, title, description, countryCode, isReleased, reportingDate, modifiedDate, periodStartYear, periodEndYear, periodDescription, obligations, isBlockedByQCError, status, statusDate, creator, hasUnknownQC, history) > array(csv)||
|**Query**|**isReleased**  <br>*optional*|Released(1) or Unreleased(0) envelopes to return|enum (, )||
|**Query**|**modifiedDate**  <br>*optional*|Return envelopes with specified modifiedDate. date format.|string(date)||
|**Query**|**modifiedDateEnd**  <br>*optional*|Return envelopes that have a modified date in range of modifiedDateStart and modifiedDateEnd. If modifiedDateStart is missing, all envelopes with modified date <= modifiedDateEnd will be returned.|string(date)||
|**Query**|**modifiedDateStart**  <br>*optional*|Return envelopes that have a modified date in range of modifiedDateStart and modifiedDateEnd or today if modifiedDateEnd is missing.|string(date)||
|**Query**|**obligations**  <br>*optional*|Return envelopes with one of the following obligations|< integer > array(csv)||
|**Query**|**periodDescription**  <br>*optional*|Return envelopes with specified periodDescription|enum (Whole Year, First Half, Second Half, First Quarter, Second Quarter, Third Quarter, Fourth Quarter, January, February, March, April, May, June, July, August, September, October, November, December)||
|**Query**|**reportingDate**  <br>*optional*|Return envelopes with this reporting date. format.|string(date)||
|**Query**|**reportingDateEnd**  <br>*optional*|Return envelopes that have a reporting date in range of reportingDateStart and reportingDateEnd. If reportingDateStart is missing, all envelopes with reporting date <= reportingDateEnd will be returned.|string(date)||
|**Query**|**reportingDateStart**  <br>*optional*|Return envelopes that have a reporting date in range of reportingDateStart and reportingDateEnd or today if reportingDateEnd is missing.|string(date)||
|**Query**|**status**  <br>*optional*|Return envelopes that have the following status|string||
|**Query**|**statusDate**  <br>*optional*|Return envelopes that have a status with the following statusDate.|string(date)||
|**Query**|**url**  <br>*optional*|Url of the envelopes or part of to return|string||


##### Responses

|HTTP Code|Description|Schema|
|---|---|---|
|**200**|List released or unreleased envelopes|[Response 200](#envelopes-get-response-200)|

<a name="envelopes-get-response-200"></a>
**Response 200**

|Name|Description|Schema|
|---|---|---|
|**envelopes**  <br>*optional*||< [Envelope](#envelope) > array|
|**errors**  <br>*optional*||< [Error](#error) > array|


##### Example HTTP response

###### Response 200
```
json :
{
  "application/json" : {
    "errors" : [ {
      "title" : "Error title",
      "description" : "This is a generic error description"
    } ],
    "envelopes" : [ {
      "files" : [ {
        "title" : "My Envelope file",
        "archived_files" : [ "File1.xml", "File2.xml" ],
        "contentType" : "application/xml",
        "uploadDate" : "2013-04-12T23:20:50.520+0000",
        "url" : "http://foo/bar/my_envelope/my_envelope_file.xml",
        "schemaURL" : "http://foo/bar/schema.xsd"
      } ],
      "periodEndYear" : 2014,
      "status" : "Release",
      "countryCode" : "RO",
      "statusDate" : "2013-04-13T01:20:50.530+0000",
      "obligations" : [ "701" ],
      "isBlockedByQCError" : 0,
      "url" : "http://foo/bar/my_envelope",
      "modifiedDate" : "2013-04-13T01:20:50.530+0000",
      "creator" : "foo",
      "history" : [ {
        "id" : 0,
        "title" : "Release",
        "activity_id" : "Release",
        "activity_status" : "complete",
        "blocker" : false,
        "modified" : "2013-04-13T01:20:50.530+0000"
      } ],
      "isReleased" : 1,
      "title" : "My Envelope",
      "reportingDate" : "2013-04-13T01:20:50.530+0000",
      "periodStartYear" : 2013,
      "description" : "A description for my envelope",
      "periodDescription" : "Whole Year"
    } ]
  }
}
```



