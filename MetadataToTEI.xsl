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
                        <sourceDesc>
                            <biblStruct>
                                <monogr>
                                    <editor>Foner, Philip S.</editor>
                                    <title>The collected writings of Thomas Paine</title>
                                    <imprint>
                                        <pubPlace>New York</pubPlace>
                                        <publisher>Citadel Press</publisher>
                                        <date>1945</date>
                                    </imprint>
                                </monogr>
                            </biblStruct>
                        </sourceDesc>
                    </fileDesc>
                    <encodingDesc>
                        <samplingDecl>
                            <p>Editorial notes in the Foner edition have not
                                been reproduced. </p>
                            <p>Blank lines and multiple blank spaces, including paragraph
                                indents, have not been preserved. </p>
                        </samplingDecl>
                        <editorialDecl>
                            <correction status="high"
                                method="silent">
                                <p>The following errors
                                    in the Foner edition have been corrected:
                                    <list>
                                        <item>p. 13 l. 7 cotemporaries contemporaries</item>
                                        <item>p. 28 l. 26 [comma] [period]</item>
                                        <item>p. 84 l. 4 kin kind</item>
                                        <item>p. 95 l. 1 stuggle struggle</item>
                                        <item>p. 101 l. 4 certainy certainty</item>
                                        <item>p. 167 l. 6 than that</item>
                                        <item>p. 209 l. 24 publshed published</item>
                                    </list>
                                </p>
                            </correction>
                            <normalization>
                                <p>No normalization beyond that performed
                                    by Foner, if any. </p>
                            </normalization>
                            <quotation marks="all">
                                <p>All double quotation marks
                                    rendered with ", all single quotation marks with
                                    apostrophe. </p>
                            </quotation>
                            <hyphenation eol="none">
                                <p>Hyphenated words that appear at the
                                    end of the line in the Foner edition have been reformed.</p>
                            </hyphenation>
                            <stdVals>
                                <p>The values of <att>when-iso</att> on the <gi>time</gi>
                                    element always end in the format <val>HH:MM</val> or
                                    <val>HH</val>; i.e., seconds, fractions thereof, and time
                                    zone designators are not present.</p>
                            </stdVals>
                            <interpretation>
                                <p>Compound proper names are marked. </p>
                                <p>Dates are marked. </p>
                                <p>Italics are recorded without interpretation. </p>
                            </interpretation>
                        </editorialDecl>
                        <classDecl>
                            <taxonomy xml:id="lcsh">
                                <bibl>Library of Congress Subject Headings</bibl>
                            </taxonomy>
                            <taxonomy xml:id="lc">
                                <bibl>Library of Congress Classification</bibl>
                            </taxonomy>
                        </classDecl>
                    </encodingDesc>
                    <profileDesc>
                        <creation>
                            <date>1774</date>
                        </creation>
                        <langUsage>
                            <language ident="en" usage="100">English.</language>
                        </langUsage>
                        <textClass>
                            <keywords scheme="#lcsh">
                                <term>Political science</term>
                                <term>United States — Politics and government —
                                    Revolution, 1775-1783</term>
                            </keywords>
                            <classCode scheme="#lc">JC 177</classCode>
                        </textClass>
                    </profileDesc>
                    <revisionDesc>
                        <change when="1996-01-22" who="#MSM"> finished proofreading </change>
                        <change when="1995-10-30" who="#LB"> finished proofreading </change>
                        <change notBefore="1995-07-04" who="#RG"> finished data entry at end of term </change>
                        <change notAfter="1995-01-01" who="#RG"> began data entry before New Year 1995 </change>
                    </revisionDesc>
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