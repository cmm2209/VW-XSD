<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:xml="http://www.w3.org/XML/1998/namespace"
    exclude-result-prefixes="xml tei">

    <xsl:output method="text"
        encoding="UTF-8"
        indent="no"/>
        
    <xsl:template match="@* | node()">
        <xsl:copy>
            <xsl:apply-templates select="@* | node()"/>
        </xsl:copy>
    </xsl:template>
    
    <xsl:template
        match="tei:*[
        not(@xml:lang)                     
        and not(ancestor::*[@xml:lang])    
        and not(descendant::*[@xml:lang])  
        and not(self::tei:TEI)            
        ]"/>
    
    <xsl:template match="tei:stage/tei:q"/>    
    
    <xsl:template match="text()">
        <!--  <xsl:value-of select="."/>  -->
        <xsl:value-of select="translate(.,'[]/','   ')"/>
    </xsl:template>
    
</xsl:stylesheet>