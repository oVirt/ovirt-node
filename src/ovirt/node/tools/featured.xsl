<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:fn="http://www.w3.org/2005/xpath-functions">

<xsl:template match="/">
  <html>
  <head>
    <title>NodeInfo</title>
    <style type="text/css">
    body { font-family: sans-serif; }
    h1   { color: white;
           background: #888;
           padding: 1em;
           margin: -.3em; }
    h1, h2, h3 { font-weight: lighter; }
    form { display: inline; }
    </style>
  </head>
  <body>
  <h1>Node Featured</h1>
  <xsl:apply-templates />
  </body>
  </html>
</xsl:template>

<xsl:template match="features">
<h2>Features</h2>
<ul>
<xsl:for-each select="feature">
    <xsl:sort select="@namespace" order="ascending"/>
    <xsl:sort select="@name" order="ascending"/>
    <xsl:call-template name="ownedobject"/>
</xsl:for-each>
</ul>
</xsl:template>

<xsl:template match="methods">
<h2>Methods</h2>
<ul>
<xsl:for-each select="method">
    <xsl:sort select="@namespace" order="ascending"/>
    <xsl:sort select="@name" order="ascending"/>
    <xsl:call-template name="ownedobject"/>
</xsl:for-each>
</ul>
</xsl:template>

<xsl:template name="ownedobject">
<li>
<abbr>
<xsl:attribute name="title">Owned by: <xsl:value-of select="@owner"/></xsl:attribute>
<b>
<xsl:value-of select="@namespace"/>/<xsl:value-of select="@name"/>
<xsl:if test="text() != ''"> = "<xsl:value-of select="text()"/>"</xsl:if>
<xsl:if test="name() = 'method'">
<form method="GET">
    <xsl:attribute name="action">
/methods/<xsl:value-of select="@namespace"/>/<xsl:value-of select="@name"/>
    </xsl:attribute>
    (
    <xsl:for-each select="arguments/argument">
        <xsl:sort select="@position" order="ascending"/>
        <xsl:value-of select="@name"/>:
        <input type="text" size="2">
            <xsl:attribute name="name">
                <xsl:value-of select="@name"/>
            </xsl:attribute>
        </input>
    </xsl:for-each>
    )
    <input type="submit" value="Invoke"/>
</form>
</xsl:if>
</b>
</abbr>
<xsl:if test="@description != ''">
 - <i><xsl:value-of select="@description"/></i>
</xsl:if>
<pre><xsl:value-of select="documentation"/></pre>
<xsl:if test="@version != ''">
<p>(v<xsl:value-of select="@version"/>)</p>
</xsl:if>
</li>
</xsl:template>


<xsl:template match="//method/result">
<h2>Result</h2>
<a href="/">Back</a>
<h3>Returnvalue</h3>
<pre>
<xsl:value-of select="retval/text()"/>
</pre>
<h3>Exception</h3>
<div style="color: red">
<pre>
<xsl:value-of select="exception/@type"/>
<xsl:value-of select="exception/text()"/>
</pre>
</div>
</xsl:template>

</xsl:stylesheet>
