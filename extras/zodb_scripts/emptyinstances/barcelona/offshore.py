## Script (Python) "offshore"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=language
##title=
##
return """<?xml version="1.0" encoding="UTF-8"?>
<offshore
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
      xmlns:xi="http://www.w3.org/2001/XInclude"
      xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/barcelona_convention/offshore.xsd" 
      xml:lang="%s">
  <reporting-party>
    <contracting-party/>
    <reporting-period-start/>
    <reporting-period-end/>
    <institution-name-full/>
    <officer-name-focalpoint/>
    <mailing-address/>
    <telephone/>
    <fax/>
    <email/>
    <contact-point-national>
      <contact-point/>
      <institution-full-name/>
      <mailing-address/>
      <telephone/>
      <fax/>
      <email/>
    </contact-point-national>
    <signature/>
    <submission-date/>
    <providers>
      <provider>
        <institution-full-name/>
        <contact-point-name/>
        <mailing-address/>
        <telephone/>
        <fax/>
        <email/>
      </provider>
    </providers>
  </reporting-party>
  <report>
    <legal-measures>
      <table>
        <exploration-exploitation-auth>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </exploration-exploitation-auth>
        <best-environmentally-techiques>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </best-environmentally-techiques>
        <disposal-prohibition>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </disposal-prohibition>
        <special-permit-annex2>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </special-permit-annex2>
        <general-permit>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </general-permit>
        <sewage-discharges>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </sewage-discharges>
        <non-biodegradable-disposal>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </non-biodegradable-disposal>
        <food-waste-disposal>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </food-waste-disposal>
        <onshore-disposal>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </onshore-disposal>
        <special-areas-protection>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </special-areas-protection>
      </table>
    </legal-measures>
    <resource-allocation>
      <table>
        <permits-section2>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </permits-section2>
        <permits-annex3>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </permits-annex3>
        <sewage-treatment-art11-para1>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </sewage-treatment-art11-para1>
        <discharges-art11-para1b>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </discharges-art11-para1b>
        <safety-measures>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </safety-measures>
        <contingency-planning>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </contingency-planning>
        <monitoring-art19>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </monitoring-art19>
        <removal-operations>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </removal-operations>
      </table>
    </resource-allocation>
    <administrative-measures>
      <table3>
        <row>
          <granted-authorizations/>
          <date/>
          <duration/>
          <activity/>
          <site/>
          <prior-special-permit>
            <substance/>
            <quantity/>
            <site/>
          </prior-special-permit>
          <prior-general-permit>
            <substances/>
            <quantity/>
            <site/>
          </prior-general-permit>
          <waste-quantity/>
          <monitoring-art19-para2/>
          <reception-art13/>
          <contingency-art16/>
          <safety-art15/>
          <restricted-measures>
            <eia/>
            <monitoring/>
            <prohibition/>
            <removal/>
            <exchange-info/>
          </restricted-measures>
        </row>
      </table3>
      <table4>
        <row>
          <date/>
          <disposal-reasons>
            <save-life/>
            <navigation-safety/>
            <damage/>
            <minimize-pollution/>
          </disposal-reasons>
          <materials/>
          <quantity/>
          <sites/>
        </row>
      </table4>
      <table5>
        <row>
          <installation-removed/>
          <date/>
          <measures>
            <navigation-safety/>
            <fishing/>
            <marine-protection/>
            <other-cp-rights/>
          </measures>
          <depth/>
          <position/>
          <location/>
        </row>
      </table5>
    </administrative-measures>
    <enforcement-measures>
      <table6>
        <national>
          <inspections/>
          <non-compliance-cases/>
          <fines/>
          <suspensions/>
          <shutdowns/>
          <other-measures/>
          <clean-measures/>
          <remarks/>
        </national>
        <specific>
          <inspections/>
          <non-compliance-cases/>
          <fines/>
          <suspensions/>
          <shutdowns/>
          <other-measures/>
          <clean-measures/>
          <remarks/>
        </specific>
        <provisions-illegal>
          <inspections/>
          <non-compliance-cases/>
          <fines/>
          <suspensions/>
          <shutdowns/>
          <other-measures/>
          <clean-measures/>
          <remarks/>
        </provisions-illegal>
        <provisions-safety>
          <inspections/>
          <non-compliance-cases/>
          <fines/>
          <suspensions/>
          <shutdowns/>
          <other-measures/>
          <clean-measures/>
          <remarks/>
        </provisions-safety>
      </table6>
    </enforcement-measures>
    <effectiveness>
      <authorizations/>
      <mediterranean-sea-surface/>
      <materials/>
      <inspections/>
      <non-compliance/>
      <non-compliance-sanctioned/>
      <burried-installations/>
    </effectiveness>
  </report>
</offshore>
"""