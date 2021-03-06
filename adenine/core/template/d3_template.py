# -*- coding: utf-8 -*-
# note: "format" this string to load data in csv format with % string
D3_TREE = r"""
<!DOCTYPE html>
<meta charset="utf-8">
<style>

.node circle {
  fill: #999;
}

.node text {
  font: 10px sans-serif;
}

.node--internal circle {
  fill: #555;
}

.node--internal text {
  text-shadow: 0 1px 0 #fff, 0 -1px 0 #fff, 1px 0 0 #fff, -1px 0 0 #fff;
}

.link {
  fill: none;
  stroke: #555;
  stroke-opacity: 0.4;
  stroke-width: 1.5px;
}

</style>
<button class="download" onClick="(function () { var e = document.createElement('script'); e.setAttribute('src', %s); e.setAttribute('class', 'svg-crowbar'); document.body.appendChild(e); })();">
    <big>⇩</big> Download SVG
  </button>
<svg width="1000" height="1000"></svg>
<script src="http://d3js.org/d3.v4.min.js"></script>
<script>

var svg = d3.select("svg"),
    width = +svg.attr("width"),
    height = +svg.attr("height"),
    g = svg.append("g").attr("transform", "translate(40,0)");

var tree = d3.cluster()
    .size([height, width - 160]);

var stratify = d3.stratify();
//    .parentId(function(d) { return d.id.substring(0, d.id.lastIndexOf(".")); });

d3.csv(%s, function(error, data) {
  if (error) throw error;

  // var root = stratify(data)
  //   .sort(function(a, b) { return (a.height - b.height) || a.id.localeCompare(b.id); });
  var root = d3.stratify()
    .id(function(d) { return d.name; })
    .parentId(function(d) { return d.parent; })
    (data);

  tree(root);

  var link = g.selectAll(".link")
      .data(root.descendants().slice(1))
    .enter().append("path")
      .attr("class", "link")
      .attr("d", function(d) {
        return "M" + d.y + "," + d.x
            + "C" + (d.parent.y + 50) + "," + d.x
            + " " + (d.parent.y + 50) + "," + d.parent.x
            + " " + d.parent.y + "," + d.parent.x;
      });

  var node = g.selectAll(".node")
      .data(root.descendants())
    .enter().append("g")
      .attr("class", function(d) { return "node" + (d.children ? " node--internal" : " node--leaf"); })
      .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; })

  node.append("circle")
      .attr("r", 5);

  node.append("text")
      .style("font-size", "20px")
      .style("font-weight", "bold")
      .attr("dy", 1)
      .attr("x", function(d) { return d.children ? -8 : 8; })
      .style("text-anchor", function(d) { return d.children ? "end" : "start"; })
      .text(function(d) { return d.children ? " " : d.id; });
});

</script>

"""
