## Script (Python) "dumping"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=language
##title=
##
return """<?xml version="1.0" encoding="UTF-8"?>
<dumping
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
      xmlns:xi="http://www.w3.org/2001/XInclude"
      xsi:noNamespaceSchemaLocation="http://biodiversity.eionet.europa.eu/schemas/barcelona_convention/dumping.xsd" 
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
        <prohibition-dumping>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </prohibition-dumping>
        <dumping-wastes>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </dumping-wastes>
        <sea-incineration>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </sea-incineration>
        <ships-aicrafts>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </ships-aicrafts>
        <ships-aircrafts-load>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </ships-aircrafts-load>
        <ships-aircrafts-dumping>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </ships-aircrafts-dumping>
        <report-incidents>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </report-incidents>
        <dump-man-made-structures>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </dump-man-made-structures>
      </table>
    </legal-measures>
    <resource-allocation>
      <table>
        <permits-issue>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </permits-issue>
        <sea-monitor-programme>
          <status-column>
            <status-type/>
            <reference/>
            <comment/>
          </status-column>
          <difficulties-column>
            <difficulty-type/>
            <comment/>
          </difficulties-column>
        </sea-monitor-programme>
      </table>
    </resource-allocation>
    <administrative-measures>
      <table>
        <row>
          <granted-permits/>
          <issue-date/>
          <validity/>
          <origin/>
          <loading-port/>
          <frequency/>
          <vessel-speed/>
          <vessel-load-rate/>
          <dumping-site>
            <length/>
            <nearest-coast/>
            <longitude/>
            <depth/>
          </dumping-site>
          <waste-form>
            <solid/>
            <liquid/>
            <mixed/>
          </waste-form>
          <waste-quantity/>
          <waste-properties>
            <solubility/>
            <ph/>
            <density/>
          </waste-properties>
          <waste-composition>
            <x/>
            <y/>
            <z/>
            <yy/>
            <zz/>
            <other/>
          </waste-composition>
          <packaging/>
          <release/>
          <cleansing/>
        </row>
      </table>
      <table4>
        <dredge>
          <cases/>
          <occurrence/>
          <ref-no-med/>
          <ref-no-cp/>
          <circumstances/>
        </dredge>
        <marine-waste>
          <cases/>
          <occurrence/>
          <ref-no-med/>
          <ref-no-cp/>
          <circumstances/>
        </marine-waste>
        <sea-structures>
          <cases/>
          <occurrence/>
          <ref-no-med/>
          <ref-no-cp/>
          <circumstances/>
        </sea-structures>
        <geo-materials>
          <cases/>
          <occurrence/>
          <ref-no-med/>
          <ref-no-cp/>
          <circumstances/>
        </geo-materials>
        <other>
          <cases/>
          <occurrence/>
          <ref-no-med/>
          <ref-no-cp/>
          <circumstances/>
        </other>
      </table4>
      <table5>
        <row>
          <category/>
          <cases/>
          <occurrence/>
          <ref-no-med/>
          <ref-no-cp/>
          <quantity/>
          <circumstances/>
          <handling/>
        </row>
      </table5>
    </administrative-measures>
    <enforcement-measures>
      <table>
        <national>
          <inspections/>
          <non-compliance/>
          <fines/>
          <suspensions/>
          <other/>
          <clean/>
          <remarks/>
        </national>
        <specific>
          <inspections/>
          <non-compliance/>
          <fines/>
          <suspensions/>
          <other/>
          <clean/>
          <remarks/>
        </specific>
        <provisions>
          <inspections/>
          <non-compliance/>
          <fines/>
          <suspensions/>
          <other/>
          <clean/>
          <remarks/>
        </provisions>
      </table>
    </enforcement-measures>
    <guidelines>
      <table>
        <row>
          <permit-number/>
          <audit/>
          <waste-options/>
          <waste-composition/>
          <dumping-site/>
          <impacts/>
          <permit-requirements/>
          <permit-evaluation/>
          <permit-conditions/>
          <consultation/>
        </row>
      </table>
      <table2>
        <row>
          <permit-number/>
          <objective/>
          <impact/>
          <reference/>
          <monitoring-programme/>
          <reporting-frequency/>
          <quality-control/>
          <quality-assurance/>
        </row>
      </table2>
    </guidelines>
    <effectiveness>
      <permits/>
      <waste-dumped/>
      <inspection/>
      <non-compliance/>
      <non-compliance-sanctioned/>
    </effectiveness>
  </report>
</dumping>
"""