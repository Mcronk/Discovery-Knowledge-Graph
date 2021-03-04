
$(document).ready(function() {



var $titles = [];

var width = $(".graph").width();
var height = $(".graph").height();

var colors = ['#00B800', '#ff6600', '#CC29A3', '#E6B800'];
var colorInd = 0;
var fixedCount = 1;
var headlines = {{ headlines|safe }};
var combo;

var bigWords= {{ bigWords|safe }};
var nodes = {{ nodes|safe }};
var links = {{ links|safe }};


var svg = d3.select(".graph").append("svg")
    .attr("width", width)
    .attr("height", height);

var link = svg.selectAll(".link");
var node = svg.selectAll(".node");

var force = d3.layout.force()
    .gravity(0)
    .friction(.3)

    .size([width, height])
    .on("tick", tick);


// loadHeadlines();
update();

// To style only selects with the my-select class
// $('.selectpicker').selectpicker();

// $("#typeSelect").css("background", "yellow");
$("#typeSelect").css("-webkit-appearance", "menulist");
// $("#typeSelect").css({"font-size": "20pt"});
// $(".selectpicker").css({"font-size": "20pt"});

// $(".selectpicker").attr("style", "display:block; color:red")

// $("#typeForm").submit(function(e){
//   e.preventDefault();
//   console.log('stop refresh');
// });

// $("#typeSelect").prop("selectedIndex", -1); // For no value
$("#typeSelect").prop("selectedIndex", 0);



// $("#typeSelect").change(function () {
$("#typesButton").click(function (e) {
  e.preventDefault();
// $("select[name=typeSelect]").change(function () {
// $("#typeForm").change(function () {
  // var end = this.value;
  // var firstDropVal = $('#pick').val();
  console.log('dropdown changed');
  // $("#typeForm").submit();

  // var selection = {
  //   "entityTypes": [$
  //   ('#typeSelect option:selected').text()]
  // };
  var selection = {
    "entityTypes": $('#typeSelect').val()
  };

  // var selection = $('#typeSelect').val();
  console.log('selection = ' + JSON.stringify(selection, null, 2));

  // var el = document.getElementsByTagName('select')[0];
  // console.log('selection = ' + JSON.stringify(el, null, 2));

  // console.log('selection = ' + JSON.stringify(selection, null, 2));

  submitTypes(selection);

});


function submitTypes(data) {



  $.ajax({
      // "contentType": 'application/x-www-form-urlencoded',
      "contentType": 'application/json',
      // "data": $(this).serialize(),
      "data": JSON.stringify(data),
      "dataType": "json",
      // "dataType": "text",
      "type": "post",
      "url": "/setType",
      "success": function(data, textStatus, jQxhr ){
        // $('#response pre').html( data );

        console.log('success message = ' + JSON.stringify(data)); // dev

        var message = {
          "date": new Date(),
          "message": data,
          "status": "OK - echoing request"
        };

        // $('#doItToIt').text('ECHO!  ' + JSON.stringify(data, null, 2));
        $('#doItToIt').text('ECHO!  ' + JSON.stringify(message, null, 2));
        // $('#doItToIt').text(JSON.stringify(data));



      },
      "error": function( jqXhr, textStatus, errorThrown ){
        console.log( errorThrown );
    }
  });



}


// $("#typeForm").submit(function(e){
//     e.preventDefault();
//     console.log('stop refresh');
// });


function update() {
	force
     .nodes(nodes)
     .links(links)
     .charge(function(d) { return -2000*(d.size/1.5); })
     .linkDistance(function(d) { return Math.pow(Math.min(d.source.size,d.target.size),3)*10;} );


  link = link.data(links);

  link.exit().remove();

  link.enter().append("line")
      .attr("class", "link");

  node = node.data(nodes);

  node.exit().remove();

  node.enter().append("text")
      .attr("class", "node")
      .call(force.drag)
      .on("click", click);

  node
      .text(function(d) { return d.text; })
      .attr("x", function(d) { return d.x; })
      .attr("y", function(d) { return d.y; })
      .attr("fill", function(d) { return d.color; })
      .attr("font-weight", function(d) { switch(d.fixed) { case 1: return 'bold'; case 0: return 'normal' }})
    .attr("font-size", function(d) { return d.size+"vh"; });

  nodes.forEach(function(o, i) {
        var bbox = node[0][i].getBBox();
        o.diff = bbox.height - (o.y-bbox.y);
        o.width = bbox.width;
        o.height = o.y - bbox.y - o.diff;
    });

  force.start();
}



function click(d) {
  if (nodes[d.index]['expand'] == 1) {
    if (d3.event.defaultPrevented) {
        nodes[d.index]['fixed'] = 1;
        }
    else {
        console.log('/click d.index = ' + d.index); // dev
        nodes[d.index]['fixed'] = 0;
        nodes[d.index]['expand'] = 0;
        fixedCount-=1;
        grabHeadlines(d);
        colors.unshift(d.color);
        nodes[d.index]['color']='white';
        nodes[d.index]['size']=1.5;
        bigWords[d.text]['expand']=0;
        links = links.filter(function(o) {

            if (o.source.index == d.index){
                if (nodes[o.target.index]['expand'] == 1) {
                    return 1;
                    }
                }
            else if (o.target.index == d.index) {
                if (nodes[o.source.index]['expand'] == 1) {
                    return 1;
                    }
                }
            else {
                return 1;
                }
            });
        nodes = nodes.filter(function(o) {

                var save = 0;
                links.forEach(function(l) {
                    console.log(o.index == l.source.index);
                    if (l.source.index == o.index || l.target.index == o.index) {
                        save = 1;
                        }
                    });
                return save;

             });
        }
   update();
   return;
   }

  else {
   if (d3.event.defaultPrevented) return;
   nodes[d.index]['expand']=1;
  $.ajax
    ({
        type: "POST",
        url: "{{ url_for('click') }}",
        contentType: 'application/json',
        dataType: 'json',
        data: JSON.stringify({'nodes': nodes, 'links': links, 'bigWords': bigWords, 'current': d.index}),
        success: function (data) {
            fixedCount+=1;
            var newNodes = data.results.nodes;
            var newLinks = data.results.links;
            headlines = data.results.headlines;

            combo = data.results.combo;
            bigWords = data.results.bigWords;
            // loadHeadlines();

            for (z=0; z<newNodes.length; z++) {
                nodes.push(newNodes[z]);
                }

            for (t=0; t<newLinks.length; t++) {
                links.push(newLinks[t]);
                }

            update();
    }});

  nodes[d.index]['color']=colors[0];
  colors.splice(0, 1);
  nodes[d.index]['size']=3
  update();
 }
}

function grabHeadlines(d) {

  console.log(combo)
  var delWord = d.text
  console.log(delWord)
  if (combo.indexOf(delWord) == 1) {
  	combo = combo.replace('"'+delWord+'"|','')
  }
  else {
  	combo = combo.replace('|"'+delWord+'"','')
  }
  console.log(combo)
    $.ajax
    ({
        type: "POST",
        url: "{{ url_for('newHeadlines') }}",
        contentType: 'application/json',
        dataType: 'json',
        data: JSON.stringify({'combo': combo}),
        success: function(data) {
            headlines = data.headlines;
            // loadHeadlines();
        }
    });

}

function download(filename, text) {
    var element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    element.setAttribute('download', filename);

    element.style.display = 'none';
    document.body.appendChild(element);

    element.click();

    document.body.removeChild(element);
}



$('.titles').on('click', 'a', function(e){
    e.preventDefault();
    var id = $(this).attr("id");

  $.ajax
    ({
        type: "POST",
        url: "{{ url_for('viewvHeadline') }}",
        contentType: 'application/json',
        dataType: 'json',
        data: JSON.stringify({'id': id}),
        success: function (data) {

            var filename = id;
            download(filename, JSON.stringify(data, null, 2));

        }
    });

});



function loadHeadlines() {
    $(".titles").empty();

    for (var fcount=fixedCount; fcount>0; fcount--) {
        var i = 0;
        if (fcount in headlines) {
            for (var c in headlines[fcount]) {
                for (var h in headlines[fcount][c]) {

                    $(".titles").append('<a href="'+headlines[fcount][c][h] +'" onclick="return false;" id="'+headlines[fcount][c][h]+'">'+ h + '<hr>');

                }
            }
        }
    }
}

function tick(e) {
  var q = d3.geom.quadtree(nodes),
      k = e.alpha*.1
      i = -1,
      n = nodes.length;


    while (++i < n) {
    o = nodes[i];

     q.visit(collide(o, e));

     }

  link.attr("x1", function(d) { return d.source.x + d.source.width/2; })
      .attr("y1", function(d) { return d.source.y - d.source.height/2; })
      .attr("x2", function(d) { return d.target.x + d.target.width/2; })
      .attr("y2", function(d) { return d.target.y - d.target.height/2; });

  node
      .attr("x", function(d) {  return d.px + (d.x - d.px); })
      .attr("y", function(d) {  return d.py + (d.y - d.py); });



}

function collide(nde, e) {
  var k = 1;
  var nx1, nx2, ny1, ny2;
  var padding = 3;
  nx1 = nde.x - padding;
  nx2 = nde.x + nde.width + padding;
  ny1 = nde.y - nde.height - padding;
  ny2 = nde.y + padding;
  return function(quad, x1, y1, x2, y2) {
     var dx, dy;
     var qx1, qx2, qy1, qy2;
     if (quad.point && (quad.point !== nde)) {
      qx1 = quad.point.x - padding;
      qx2 = quad.point.x + quad.point.width + padding;
      qy1 = quad.point.y - quad.point.height - padding;
      qy2 = quad.point.y + padding;
      dx = Math.min(nx2 - qx1, qx2 - nx1)/2;
      dy = Math.min(ny2 - qy1, qy2 - ny1)/2;
      if (dx >= 0 && dy >= 0) {
        if (dy == Math.min(dx,dy)) {
          if ((ny1 + (ny2-ny1)/2) <= (qy1 + (qy2 - qy1)/2)) {
             nde.y -= dy*k;
             quad.point.y += dy*k;
             return
          }
          if ((ny1 + (ny2-ny1)/2) > (qy1 + (qy2 - qy1)/2)) {

             nde.y += dy*k;
             quad.point.y -= dy*k;
             return
          }
          return
        }
        if (dx == Math.min(dx,dy)) {
          if ((nx1 + (nx2-nx1)/2) <= (qx1 + (qx2 - qx1)/2)) {

             nde.x -= dx*k;
             quad.point.x += dx*k;
             return
          }
          if ((nx1 + (nx2-nx1)/2) > (qx1 + (qx2 - qx1)/2)) {

             nde.x += dx*k;
             quad.point.x -= dx*k;
             return
          }
          return
        }

      }
    }

    return x1 > nx2 || x2 < nx1 || y1 > ny2 || y2 < ny1;
  };

}







});
