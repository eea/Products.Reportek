## Script (Python) "EnvelopeAddELVInstancefile"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=workitem_id, REQUEST
##title=Add an empty instance file to envelope
##
# Notice: Maintain the instancefile under /xmlexports, then cut-and-paste it to here
# when changed

context.manage_addDocument('questionnaire.xml',"ELV questionnaire",
   """<?xml version="1.0" encoding="UTF-8"?>
<questionnaire xml:lang="en"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:noNamespaceSchemaLocation="http://waste.eionet.eu.int/schemas/dir200053ec/schema.xsd">
	<q1-1/>
	<q1-1-1/>
	<q1-1-2/>
	<q1-2/>
	<q1-3/>
	<q1-4/>
	<q1-4-1/>
	<q1-5/>
	<q1-5-1/>
	<q1-5-2/>
	<q1-6/>
	<q1-6-1/>
	<q1-6-2/>
	<q1-7/>
	<q1-7-1/>
	<q1-7-2/>
	<q1-8/>
	<q1-8-1/>
	<q1-8-2/>
	<q1-9/>
	<q1-9-1/>
	<q1-9-2/>
	<q1-9-3/>
	<q1-9-3-1/>
	<q1-9-4/>
	<q1-9-5/>
	<q1-9-6/>
	<q1-9-7/>
	<q1-10/>
	<q1-10-1/>
	<q1-10-2/>
	<q1-11/>
	<q1-11-1/>
	<q1-11-2/>
	<q1-12/>
	<q1-12-1/>
	<q1-12-2/>
	<q1-13/>
	<q1-13-1/>
	<q1-13-2/>
	<q1-13-3/>
	<q1-13-4/>
	<q1-13-5/>
	<q1-13-6/>
	<q1-14/>
	<q1-14-1/>
	<q1-14-2/>
	<q1-15/>
	<q1-15-1/>
	<q1-15-2/>
	<q1-16/>
	<q1-16-1/>
	<q1-16-2/>
	<q1-17/>
	<q1-17-1/>
	<q1-17-2/>
	<q1-18/>
	<q1-18-1/>
	<q1-18-2/>
	<q1-18-3/>
	<q1-18-4/>
	<q1-19/>
	<q1-19-1/>
	<q1-19-2/>
	<q1-20/>
	<q1-20-1/>
	<q1-20-2/>
	<q1-21/>
	<q1-21-1/>
	<q1-21-2/>
	<q1-22/>
	<q1-22-1/>
	<q1-22-2/>
	<q2-1/>
	<q2-1-1/>
	<q2-2/>
	<q2-3>
	    <value type="number" label="No. of vehicles">
		<collected label="2002"/>
		<collected label="2003"/>
		<collected label="2004"/>
            </value>
	    <q2-3c label="Comments"/>
	</q2-3>
	<q2-4>
	    <value type="number" label="No. of treatment facilities">
		<collected label="Authorised"/>
		<collected label="Registered"/>
            </value>
	    <q2-4c label="Comments"/>
	</q2-4>
	<q2-5>
	       <value type="number" label="No. of ELV with no or negative market value">
			<collected label="2002"/>
			<collected label="2003"/>
			<collected label="2004"/>
		</value>
		<value type="average" label="Average negative value">
			<collected label="2002"/>
			<collected label="2003"/>
			<collected label="2004"/>
		</value>
	    <q2-5c label="Comments"/>
	</q2-5>
	<q2-6/>
	<q2-7/>
	<q2-7-1/>
	<q2-8>
		<value type="reuse" label="Rate of reuse">
			<collected label="2002"/>
			<collected label="2003"/>
			<collected label="2004"/>
		</value>
		<value type="recycling" label="Rate of recycling">
			<collected label="2002"/>
			<collected label="2003"/>
			<collected label="2004"/>
		</value>
		<value type="recovery" label="Rate of recovery">
			<collected label="2002"/>
			<collected label="2003"/>
			<collected label="2004"/>
		</value>
	    <q2-8c label="Comments"/>
	</q2-8>
	<q2-9/>
	<q2-10/>
</questionnaire>
""",'text/xml','')
    
context.completeWorkitem(workitem_id)
