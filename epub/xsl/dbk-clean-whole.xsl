<?xml version="1.0" ?>
<xsl:stylesheet 
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
  xmlns:mml="http://www.w3.org/1998/Math/MathML"
  xmlns:c="http://cnx.rice.edu/cnxml"
  xmlns:db="http://docbook.org/ns/docbook"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:md="http://cnx.rice.edu/mdml/0.4" xmlns:bib="http://bibtexml.sf.net/"
  xmlns:xi="http://www.w3.org/2001/XInclude"
  version="1.0">

<xsl:import href="debug.xsl"/>
<xsl:import href="ident.xsl"/>

<xsl:output indent="yes" method="xml"/>

<!-- Collapse XIncluded modules -->
<xsl:template match="db:chapter[count(db:section)=1]">
	<xsl:call-template name="cnx.log"><xsl:with-param name="msg">INFO: Converting module to chapter</xsl:with-param></xsl:call-template>
	<xsl:copy>
		<xsl:apply-templates select="@*|db:section/@*"/>
		<xsl:choose>
			<xsl:when test="db:info">
				<xsl:call-template name="cnx.log"><xsl:with-param name="msg">INFO: Discarding original module title</xsl:with-param></xsl:call-template>
				<xsl:apply-templates select="db:info"/>
				<xsl:apply-templates select="db:section/*[local-name() != 'info']"/>
			</xsl:when>
			<xsl:otherwise>
				<xsl:apply-templates select="db:section/node()"/>
			</xsl:otherwise>
		</xsl:choose>
	</xsl:copy>
</xsl:template>


<!-- Boilerplate -->
<xsl:template match="/">
	<xsl:apply-templates select="*"/>
</xsl:template>

<xsl:template match="db:informalequation">
	<db:equation>
		<xsl:apply-templates select="@*"/>
		<db:title/>
		<xsl:apply-templates select="node()"/>
	</db:equation>
</xsl:template>

<xsl:template match="db:informalexample">
	<db:example>
		<xsl:apply-templates select="@*"/>
		<db:title/>
		<xsl:apply-templates select="node()"/>
	</db:example>
</xsl:template>

<xsl:template match="db:informalfigure">
	<db:figure>
		<xsl:apply-templates select="@*"/>
		<db:title/>
		<xsl:apply-templates select="node()"/>
	</db:figure>
</xsl:template>


<!-- If the Module title starts with the chapter title then discard it. -->
<xsl:template match="db:PHIL/db:chapter/db:section">
	<xsl:choose>
		<xsl:when test="starts-with(db:info/db:title/text(), ../db:info/db:title/text())">
			<xsl:call-template name="cnx.log"><xsl:with-param name="msg">WARNING: Stripping chapter name from title</xsl:with-param></xsl:call-template>
			<xsl:copy>
				<xsl:copy-of select="@*"/>
				<db:info>
					<xsl:apply-templates mode="strip-title" select="db:info/db:title"/>
					<xsl:apply-templates select="db:info/*[local-name()!='title']|db:info/processing-instruction()|db:info/comment()"/>
				</db:info>
				<xsl:apply-templates select="*[local-name()!='info']|processing-instruction()|comment()"/>
			</xsl:copy>
		</xsl:when>
		<xsl:otherwise>
			<xsl:copy>
				<xsl:copy-of select="@*"/>
				<xsl:apply-templates/>
			</xsl:copy>
		</xsl:otherwise>
	</xsl:choose>
</xsl:template>
<xsl:template mode="strip-title" match="db:title">
	<xsl:variable name="chapTitle">
		<xsl:value-of select="../../../db:info/db:title/text()"/>
		<xsl:text>: </xsl:text>
	</xsl:variable>
	<xsl:copy>
		<xsl:copy-of select="@*"/>
		<xsl:for-each select="node()">
			<xsl:choose>
				<xsl:when test="position()=1">
					<xsl:value-of select="substring-after(., $chapTitle)"/>
				</xsl:when>
				<xsl:otherwise>
					<xsl:apply-templates select="."/>
				</xsl:otherwise>
			</xsl:choose>
		</xsl:for-each>
	</xsl:copy>
</xsl:template>

<!-- Combine all module glossaries into a single book glossary -->
<xsl:template match="db:book">
	<xsl:copy>
		<xsl:copy-of select="@*"/>
		<!-- Generate a list of authors from the modules -->
		<xsl:apply-templates/>
		<xsl:if test="//db:chapter/db:section/db:glossary">
			<db:glossary>
				<xsl:apply-templates select="//db:chapter/db:section/db:glossary/*"/>
			</db:glossary>
		</xsl:if>
	</xsl:copy>
</xsl:template>
<!-- Discard matches for db:chapter/db:section/db:glossary -->
<xsl:template match="db:chapter/db:section/db:glossary">
	<!-- Discard this. it's handled in match="db:book" -->
</xsl:template>

<!-- Discard extra db:info in db:section (modules) except for db:title -->
<!-- This way we don't have attribution for every db:section (module) -->
<xsl:template match="db:section/db:info/db:*[not(self::db:title)]"/>

<!-- Move the solutions to exercises (db:qandaset) to the end of the chapter. -->
<!-- 
<xsl:template match="db:question[../db:answer]">
	<xsl:copy>
		<xsl:apply-templates select="@*|node()"/>
		<db:para><db:link xlink:href="{ancestor::db:section[@xml:id]/@xml:id}.solution">Solution</db:link></db:para>
	</xsl:copy>
</xsl:template>
<xsl:template match="db:answer"/>
<xsl:template match="db:chapter[.//db:qandaset]">
	<xsl:copy>
		<xsl:apply-templates select="@*|node()"/>
		<db:section>
			<db:title>Solutions to Exercises</db:title>
			<xsl:apply-templates mode="cnx.solution" select=".//db:qandaset"/>
		</db:section>
	</xsl:copy>
</xsl:template>
<xsl:template mode="cnx.solution" match="db:qandaset">
	<db:formalpara>
		<db:title><xsl:apply-templates select="ancestor::db:*[db:title][2]/db:title/node()"/></db:title>
		<xsl:apply-templates mode="cnx.solution"/>
	</db:formalpara>
</xsl:template>
<xsl:template mode="cnx.solution" match="db:qandaentry">
	<xsl:value-of select="position()"/>
	<xsl:text>. </xsl:text>
	<xsl:apply-templates mode="cnx.solution"/>
	<xsl:text> </xsl:text>
</xsl:template>
<xsl:template mode="cnx.solution" match="db:answer">
	<xsl:apply-templates mode="cnx.solution"/>
</xsl:template>
<xsl:template mode="cnx.solution" match="db:para">
	<xsl:apply-templates mode="cnx.solution"/>
</xsl:template>
<xsl:template mode="cnx.solution" match="db:question"/>
<xsl:template mode="cnx.solution" match="*">
	<xsl:call-template name="cnx.log"><xsl:with-param name="msg">ERROR: Skipped in creating a solution</xsl:with-param></xsl:call-template>
	<xsl:copy>
		<xsl:apply-templates select="@*|node()"/>
	</xsl:copy>
</xsl:template>
 -->
</xsl:stylesheet>