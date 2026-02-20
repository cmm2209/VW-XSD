<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:hei="https://digi.ub.uni-heidelberg.de/schema/tei/heiEDITIONS"
    exclude-result-prefixes="tei hei">
    
    <!-- 1.  Default “do‑nothing” template (keeps the document stripped) -->
    <xsl:template match="node()|@*"/>
    
    <!-- 2.  Keep the TEI root -->
    <xsl:template match="tei:TEI">
        <xsl:copy>
            <xsl:apply-templates select="node()"/>
        </xsl:copy>
    </xsl:template>
    
    <!-- 3.  Keep the text, body, etc. -->
    <xsl:template match="tei:text">
        <xsl:copy>
            <xsl:apply-templates select="@* | node()"/>
        </xsl:copy>
    </xsl:template>
    
    <xsl:template match="tei:body">
        <xsl:copy>
            <xsl:apply-templates select="@* | node()"/>
        </xsl:copy>
    </xsl:template>
    
    <xsl:template match="tei:teiHeader"/>
    
    <xsl:template match="hei:initial">
        <!-- output the string‑value of the element (its character data) -->
        <xsl:value-of select="."/>
    </xsl:template>
    
    <!-- 4.  Elements that you want to keep (copy them unchanged) -->
    <xsl:template match="
        tei:div | tei:head | tei:p | tei:lb | tei:l | tei:seg | tei:lg |
        tei:pb | tei:milestone"
        priority="2">
        <xsl:copy>
            <!-- copy every attribute (except xml:id – see template #9) -->
            <xsl:apply-templates select="@*"/>
            <!-- recurse – only allowed children (or text) will survive -->
            <xsl:apply-templates select="node()"/>
        </xsl:copy>
    </xsl:template>
    
    <xsl:template match="tei:line" priority="2">
        <xsl:element name="l" namespace="http://www.tei-c.org/ns/1.0">
            <xsl:apply-templates select="@* | node()"/>
        </xsl:element>
    </xsl:template>
    
    <xsl:template match="tei:milestone//text()">
        <xsl:copy/>
    </xsl:template>
    
    <xsl:template match="@xml:id"/>
    
    <xsl:template match="text()[normalize-space(.)='']"/>
    
    
    <xsl:template match="@*">
        <xsl:copy/>
    </xsl:template>
    
    <xsl:template match="text()">
      <!--  <xsl:value-of select="."/>  -->
        <xsl:value-of select="translate(.,'ýẏſuͤ','yysü')"/>
    </xsl:template>
    
    <xsl:template match="tei:choice" priority="3">
        <!-- The <expan> element is also in the TEI namespace -->
        <xsl:value-of select="tei:expan"/>
    </xsl:template>
    
    <xsl:output method="xml"
        encoding="UTF-8"
        indent="yes"/>
</xsl:stylesheet>