<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    exclude-result-prefixes="xs"
    version="2.0">
    
    <xsl:template match="/">
        <teiCorpus xmlns="http://www.tei-c.org/ns/1.0">
            <teiHeader>
               <!-- corpus-level metadata here --> 
                <fileDesc>
                    <titleStmt>
                        <title>The Text Corpus of the Scientific Discourse in Medieval Vernacular Texts Project</title>
                        <principal>Prof. Dr. Racha Kirakosian</principal>
                        <funder>VolkswagenStiftung</funder>
                    </titleStmt>
                    <publicationStmt>
                        <p>To be determined.</p>
                    </publicationStmt>
                    <sourceDesc>
                        <p>A corpus of digitized dialogues and dialogue-containing sources in Mittelhochdeutsch.</p>
                    </sourceDesc>
                </fileDesc>
            </teiHeader>
            <TEI>
                <teiHeader>
                    <fileDesc>
                        <titleStmt>
                            <title>
                                <xsl:attribute name="ref"><xsl:value-of select="radarFile/relatedIdentifiers/relatedIdentifier/@schemeURI"/><xsl:value-of select="radarFile/relatedIdentifiers/relatedIdentifier"/></xsl:attribute>
                                <xsl:value-of select="radarFile/title"/>
                            </title>
                            
                            <xsl:for-each select="radarFile/additionalTitles">
                                <xsl:if test="additionalTitle != ''">
                                    <title>
                                       <xsl:attribute name="type"><xsl:value-of select="additionalTitle/@additionalTitleType"/></xsl:attribute>
                                       <xsl:value-of select="additionalTitle"/>
                                    </title>
                                </xsl:if>
                            </xsl:for-each>
                            
                            <author>
                                <xsl:attribute name="ref"><xsl:value-of select="radarFile/creators/creator/nameIdentifier/@schemeURI"/><xsl:value-of select="radarFile/creators/creator/nameIdentifier"/></xsl:attribute>
                                <xsl:value-of select="radarFile/creators/creator/creatorName"/>
                            </author>
                            
                        <xsl:for-each select="radarFile/contributors/contributor">
                            <xsl:if test="@contributorType='Editor'">
                                <editor>
                                    <xsl:attribute name="ref"><xsl:value-of select="nameIdentifier/@schemeURI"/><xsl:value-of select="nameIdentifier"/></xsl:attribute>
                                    <xsl:value-of select="contributorName"/>
                                </editor>
                            </xsl:if>
                        </xsl:for-each>
                    
                        <xsl:for-each select="radarFile/contributors/contributor">
                            <xsl:if test="@contributorType='DataCollector'">
                                <respStmt>
                                    <resp>Data collected by</resp>
                                    <name>
                                        <xsl:attribute name="ref"><xsl:value-of select="nameIdentifier/@schemeURI"/><xsl:value-of select="nameIdentifier"/></xsl:attribute>
                                        <xsl:value-of select="contributorName"/></name>
                                </respStmt>     
                            </xsl:if>
                        </xsl:for-each> 
                      </titleStmt>
                        <xsl:for-each select="radarFile/resource">
                            <xsl:if test="@resourceType='CriticalEdition'">
                                <editionStmt>
                                    <edition>
                                        <p><xsl:value-of select="edition"/></p>
                                        <date>
                                            <xsl:value-of select="date"/>
                                        </date>
                                    </edition>
                                </editionStmt>
                            </xsl:if>
                        </xsl:for-each>
                        <publicationStmt>
                            <p>To be determined.</p>
                        </publicationStmt>
                        
                        <xsl:for-each select="radarFile/descriptions">
                            <xsl:if test="description != ''">
                                <notesStmt>
                                    <note>
                                        <xsl:attribute name="type"><xsl:value-of select="description/@descriptionType"/></xsl:attribute>
                                        <xsl:value-of select="description"/>
                                    </note>
                                </notesStmt>
                            </xsl:if>
                        </xsl:for-each>
                        
                        <sourceDesc>
                            <xsl:for-each select="radarFile/resource">
                                <xsl:choose>
                                    <xsl:when test="@resourceType='Manuscript'">
                                       <msDesc>
                                           <msIdentifier>
                                               <settlement><xsl:value-of select="settlement"/></settlement>
                                               <institution><xsl:value-of select="institution"/></institution>
                                               <repository><xsl:value-of select="repository"/></repository>
                                               <idno><xsl:value-of select="idno"/></idno>
                                               <citedRange><xsl:value-of select="citedRange"/></citedRange>
                                               <ptr><xsl:value-of select="ptr"/></ptr>
                                           </msIdentifier>
                                       </msDesc> 
                                    </xsl:when>
                                    <xsl:otherwise>
                                        <bibl>
                                            <author><xsl:value-of select="author"/></author>
                                            <title><xsl:value-of select="title"/></title>
                                            <editor><xsl:value-of select="editor"/></editor>
                                            <edition><xsl:value-of select="edition"/></edition>
                                            <pubPlace><xsl:value-of select="pubPlace"/></pubPlace>
                                            <publisher><xsl:value-of select="publisher"/></publisher>
                                            <date><xsl:value-of select="date"/></date>
                                            <ptr><xsl:value-of select="ptr"/></ptr>    
                                        </bibl>
                                    </xsl:otherwise>
                                </xsl:choose>
                            </xsl:for-each>
                        </sourceDesc>                         
                    </fileDesc>
                    
                    <encodingDesc>
                        <projectDesc>
                            <p><xsl:value-of select="radarFile/processing/dataProcessing"/></p>
                            <p>Text processed using <xsl:value-of select="radarFile/software/softwareType/softwareName"/>.</p>
                        </projectDesc>
                    </encodingDesc>
                    <profileDesc>
                        <creation>
                            <date><xsl:value-of select="radarFile/productionYear"/></date>
                        </creation>
                        <xsl:for-each select="radarFile/languages">
                            <xsl:choose>
                                <xsl:when test="language='gmh'">
                                    <langUsage>
                                    <language ident="gmh">Mittelhochdeutsch</language>
                                </langUsage>
                                </xsl:when>
                                <xsl:when test="language='lat'">
                                    <langUsage>
                                        <language ident="lat">Latin</language>
                                    </langUsage>   
                                </xsl:when>
                                <xsl:otherwise>
                                    <langUsage>
                                        <language ident="lat">
                                            <xsl:attribute name="ident"><xsl:value-of select="language"/></xsl:attribute>
                                            <xsl:value-of select="language"/>
                                        </language>
                                    </langUsage>
                                </xsl:otherwise>
                            </xsl:choose>
                        </xsl:for-each>
                        <textClass>
                            <xsl:for-each select="radarFile/keywords/keyword">
                                <keywords>
                                    <xsl:for-each select=".">
                                        <xsl:choose>
                                            <xsl:when test="@keywordScheme='Other'"></xsl:when>
                                            <xsl:otherwise>
                                                <xsl:attribute name="scheme"><xsl:value-of select="@schemeURI"/><xsl:value-of select="@classificationCode"/></xsl:attribute></xsl:otherwise>
                                        </xsl:choose>
                                    </xsl:for-each>
                                    <term><xsl:value-of select="."/></term>
                                </keywords>
                            </xsl:for-each>    
                        </textClass>  
                    </profileDesc>
               </teiHeader>
                <text>
                    <body>
                        <p></p>
                    </body>
                </text>
            </TEI> 
        </teiCorpus>
    </xsl:template>
</xsl:stylesheet>