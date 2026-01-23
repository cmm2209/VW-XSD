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
                            <title ref="{radarFile/relatedIdentifiers/relatedIdentifiers/@schemeURI}/{radarFile/relatedIdentifiers/relatedIdentifiers}">
                                <xsl:value-of select="radarFile/title"/>
                            </title>
                            <author><xsl:value-of select="radarFile/creators/creator" disable-output-escaping="yes"/></author>
                            <respStmt>
                                <xsl:for-each select="radarFile/contributors/contributor">
                                    <resp><xsl:value-of select="radarFile/contributors/contributor/@contributorType"/>:</resp>
                                    <name><xsl:value-of select="radarFile/contributors/contributor/contributorName"/></name>
                                </xsl:for-each> 
                            </respStmt>
                        </titleStmt>
                        <xsl:if test="radarFile/resource/@resourcetype = CriticalEdition">
                            <editionStmt>
                                <edition>
                                    <p><xsl:value-of select="radarFile/resource/edition"/></p>
                                    <date><xsl:value-of select="radarFile/resource/date"/></date>
                                </edition>
                            </editionStmt>
                        </xsl:if>
                        <publicationStmt>
                            <p>To be determined.</p>
                        </publicationStmt>
                        <notesStmt>
                            <note>Funding provided by the VolkswagenStiftung.</note>
                        </notesStmt>
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