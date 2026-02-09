<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    exclude-result-prefixes="tei">
    
    <xsl:output method="text"
        encoding="UTF-8"
        indent="no"/>
          
    <xsl:template match="tei:teiHeader"/>
    
    <xsl:template match="TEI/text">
        <xsl:for-each select="l | head | p">
            <xsl:value-of select="."/>
            <xsl:text>&#10;</xsl:text>    
        </xsl:for-each>   
    </xsl:template>
    
    
</xsl:stylesheet>