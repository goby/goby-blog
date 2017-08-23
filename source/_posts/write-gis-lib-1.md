---
title: 一步一步写GIS库 1. 基本结构
keywords: "GIS, tutorial"
date: 2013-11-30 00:00:00
uuid: 5f6db065-38d1-4b64-af20-de632aa0f395
tags:
 - tutorial
---

一般的GIS的程序库和其他应用没什么区别，整个结构大致可以分成三部分：

1. 数据结构
2. 数据组织
3. 数据渲染

数据结构
===

数据结构从根本分为**矢量**和**栅格**两种类型。

栅格
---

对于栅格，因为移动设备关系，不太可能加载遥感数据，因此可能就是普通的格网+纹理贴图方式解决 ( Texture )，又因我们地图要缩放，所以需要组织不同缩放级别下的数据，因此需要 LOD( Level of Detail ) 和四叉树 ( QuadTree )。

矢量
---

数据结构从最基本的几何体开始（点、线、面、体），以及集合体加上属性之后形成的要素类型。( Geometry + Feature )

现在将一个物体在一个空间中表现出来，那么就需要给这个空间建立坐标系（方便起见一般都是直角坐标系或者地心坐标）来表示空间相对关系和大小，平面几何仅仅是小范围可用，对于地理空间来说，地球表面的球面变换尤为重要，因此不仅需要坐标系统（Coordination System），还需要坐标变换系统 ( Project )。

数据组织
===

为了方便管理，一般会对数据进行分层，比如我们常见的地图应用中，从上往下有：兴趣点 ( POI: Point of Interesting )、地标标注（Annotation）、查询数据（路线、交通流量等）、线状地物（道路网、行政边界等）、面状地物（行政区域、建筑物）、栅格底图。分层管理有个好处就是可以进行层过滤，简化数据的组织难度，方便渲染。

以上几种的图层可以大致分为三类： 
1. 标注层（Annotation Layer）：矢量文字的渲染
2. 矢量层（Vector Layer）：矢量数据
3. 栅格层（Tiled Layer）：切割成规则瓦片的栅格图所在的层

对于矢量层， 矢量数据类型很多，因此可以对矢量数据进行归类管理，即从数据个体 --> 数据类(Class) --> 数据集(Set)。

数据渲染
===

数据渲染可能根据不同数据类型渲染，基础的就是颜色（Color）、纹理（Texture）、光线（Lighting）、着色器（Shader），基本可以看成是OpenGL  ES的问题了。


总结
====

数据类型有：
1. Vertor (2-3位，用来表示Vertex)
2. Geometry ( Point、Polyline、Polygon )
3. Feature (Geometry +Fields)
4. FeatureClass ( Multi-Feature )
5. FeatureSet (Multi-FeatureClass)
6. CoordSystem
7. QuadTree
8. Texture

数据组织有：
1. Layer
2. AnnotationLayer
3. VectorLayer
4. TiledLayer

数据渲染差不多就是对OpenGL ES的封装了。

为了简化整个过程，将使用一些开源库（空间操作、分析），下一篇说说即将用到的一些开源库。

{# Local Variables: #}
{# mode: markdown   #}
{# End:             #}
