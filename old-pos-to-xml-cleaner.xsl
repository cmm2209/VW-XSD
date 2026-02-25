<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    exclude-result-prefixes="xs"
    version="1.0">
    
    <xsl:template match="/">
        <body>
            <xsl:for-each select="body/w">
                <xsl:choose>
                    <xsl:when test="@pos = '$_'">
                        <xsl:choose>
                            <xsl:when test="@norm = '.'">
                                <pc>
                                    <xsl:attribute name="pos">#.</xsl:attribute>
                                    <xsl:value-of select="token"/>
                                </pc>
                            </xsl:when>
                            <xsl:when test="@norm = '!'">
                                <pc>
                                    <xsl:attribute name="pos">#.</xsl:attribute>
                                    <xsl:value-of select="token"/>
                                </pc>
                            </xsl:when>
                            <xsl:when test="@norm = '?'">
                                <pc>
                                    <xsl:attribute name="pos">#.</xsl:attribute>
                                    <xsl:value-of select="token"/>
                                </pc>
                            </xsl:when>
                            <xsl:when test="@norm = ':'">
                                <pc>
                                    <xsl:attribute name="pos">#.</xsl:attribute>
                                    <xsl:value-of select="token"/>
                                </pc>
                            </xsl:when>
                            <xsl:when test="@norm = ';'">
                                <pc>
                                    <xsl:attribute name="pos">#.</xsl:attribute>
                                    <xsl:value-of select="token"/>
                                </pc>
                            </xsl:when>   
                            <xsl:otherwise>
                                <pc>
                                    <xsl:attribute name="pos">#(</xsl:attribute>
                                    <xsl:value-of select="token"/>
                                </pc>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:when>
                    <xsl:when test="@norm = ','">
                        <pc>
                            <xsl:attribute name="pos">#,</xsl:attribute>
                            <xsl:value-of select="token"/>
                        </pc>
                    </xsl:when>
                    <xsl:when test="@pos != ''">
                        <w>
                            <xsl:attribute name="pos"><xsl:value-of select="@pos"/></xsl:attribute>
                            <xsl:attribute name="norm"><xsl:value-of select="@norm"/></xsl:attribute>
                            <xsl:attribute name="lemma"><xsl:value-of select="@lemma"/></xsl:attribute>
                            <xsl:value-of select="token"/>
                        </w>                            
                    </xsl:when>
                </xsl:choose>
            </xsl:for-each>  
        </body>
    </xsl:template>
</xsl:stylesheet>