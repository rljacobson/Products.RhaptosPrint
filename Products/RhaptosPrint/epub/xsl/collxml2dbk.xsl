<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
  xmlns:col="http://cnx.rice.edu/collxml"
  xmlns:md="http://cnx.rice.edu/mdml"
  xmlns:db="http://docbook.org/ns/docbook"
  xmlns:xi='http://www.w3.org/2001/XInclude'
  exclude-result-prefixes="col md"
  >
<xsl:include href="cnxml2dbk.xsl"/>

<xsl:output indent="yes"/>

<xsl:template match="col:*/@*">
	<xsl:copy/>
</xsl:template>

<xsl:template match="col:collection">
	<db:book><xsl:apply-templates select="@*|node()"/></db:book>
</xsl:template>

<xsl:template match="col:metadata">
	<db:info><xsl:apply-templates select="@*|node()"/></db:info>
</xsl:template>

<!-- Modules before the first subcollection are preface frontmatter -->
<xsl:template match="col:collection/col:content[col:subcollection and col:module]/col:module[not(preceding-sibling::col:subcollection)]" priority="100">
	<db:preface>
		<xsl:apply-templates select="@*|node()"/>
		<xi:include href="{@document}/index.dbk"/>
	</db:preface>
</xsl:template>

<!-- Modules after the last subcollection are appendices -->
<xsl:template match="col:collection/col:content[col:subcollection and col:module]/col:module[not(following-sibling::col:subcollection)]" priority="100">
<!-- <db:appendix> -->
	<db:chapter>
		<xsl:apply-templates select="@*|node()"/>
		<xi:include href="{@document}/index.dbk"/>
	</db:chapter>
<!-- </db:appendix> -->
</xsl:template>


<!-- Free-floating Modules in a col:collection should be treated as Chapters -->
<xsl:template match="col:collection/col:content/col:module"> 
	<!-- TODO: Convert the db:section root of the module to a chapter. Can't now because we create xinclude refs to it -->
	<db:chapter>
		<xsl:apply-templates select="@*|node()"/>
		<xi:include href="{@document}/index.dbk"/>
	</db:chapter>
</xsl:template>

<xsl:template match="col:collection/col:content/col:subcollection">
	<db:chapter><xsl:apply-templates select="@*|node()"/></db:chapter>
</xsl:template>

<!-- Subcollections in a chapter should be treated as a section -->
<xsl:template match="col:subcollection/col:content/col:subcollection">
	<db:section><xsl:apply-templates select="@*|node()"/></db:section>
</xsl:template>

<xsl:template match="col:content">
	<xsl:apply-templates/>
</xsl:template>

<xsl:template match="col:module">
	<xi:include href="{@document}/index.dbk"/>
</xsl:template>


<xsl:template match="md:title">
	<db:title><xsl:apply-templates/></db:title>
</xsl:template>



<xsl:template match="@id|@xml:id|comment()|processing-instruction()">
    <xsl:copy/>
</xsl:template>

</xsl:stylesheet>
