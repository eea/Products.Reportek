
<a name="paths"></a>
## Resources

<a name="envelopes_resource"></a>
### Envelopes

<a name="envelopes-get"></a>
#### GET /envelopes

##### Parameters

|Type|Name|Description|Schema|Default|
|---|---|---|---|---|
|**Query**|**countryCode**  <br>*optional*|Country code in ISO "ALPHA-2 Code format for envelopes to return|string||
|**Query**|**isReleased**  <br>*optional*|Released(1) or Unreleased(0) envelopes to return|integer||
|**Query**|**modifiedDate**  <br>*optional*|Return envelopes with specified modifiedDate. ISO8601(YYYY-MM-DD) date format.|string||
|**Query**|**modifiedDateEnd**  <br>*optional*|Return envelopes that have a modified date in range of modifiedDateStart and modifiedDateEnd. If modifiedDateStart is missing, all envelopes with modified date <= modifiedDateEnd will be returned. ISO8601(YYYY-MM-DD) date format.|string||
|**Query**|**modifiedDateStart**  <br>*optional*|Return envelopes that have a modified date in range of modifiedDateStart and modifiedDateEnd or today if modifiedDateEnd is missing. ISO8601(YYYY-MM-DD) date format.|string||
|**Query**|**obligations**  <br>*optional*|Return envelopes with one of the following obligations|< integer > array||
|**Query**|**periodDescription**  <br>*optional*|Return envelopes with specified periodDescription|string||
|**Query**|**reportingDate**  <br>*optional*|Return envelopes with this reporting date. ISO8601(YYYY-MM-DD) date format.|string||
|**Query**|**reportingDateEnd**  <br>*optional*|Return envelopes that have a reporting date in range of reportingDateStart and reportingDateEnd. If reportingDateStart is missing, all envelopes with reporting date <= reportingDateEnd will be returned. ISO8601(YYYY-MM-DD) date format.|string||
|**Query**|**reportingDateStart**  <br>*optional*|Return envelopes that have a reporting date in range of reportingDateStart and reportingDateEnd or today if reportingDateEnd is missing. ISO8601(YYYY-MM-DD) date format.|string||
|**Query**|**status**  <br>*optional*|Return envelopes that have the following status|string||
|**Query**|**statusDate**  <br>*optional*|Return envelopes that have a status with the following statusDate. ISO8601(YYYY-MM-DD) date format.|string||
|**Query**|**url**  <br>*optional*|Url of the envelopes or part of to return|string||


##### Responses

|HTTP Code|Description|Schema|
|---|---|---|
|**200**|List released or unreleased envelopes|< [EnvelopeDefaultAttributes](#envelopedefaultattributes) > array|



