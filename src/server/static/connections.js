var nr_shown = 0
var json_response = ""
var map = L.map('mapid').setView([52.520008, 13.404954], 13);
var markerGroup = L.layerGroup()
var isochroneGroup = L.layerGroup()
var Esri_WorldTopoMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}', {
	attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), and the GIS User Community',
  zoomControl: true,
  maxZoom : 16
}).addTo(map);

map.zoomControl.setPosition('topright');

var command = L.control({
    position: 'topleft'
});
command.onAdd = function(map) {
    var div = L.DomUtil.create('div', 'command');

    div.innerHTML = '<i class="material-icons md-36 show" onclick ="show_sidebar()" style="cursor: pointer;background-color: rgba(255,255,255,0.6);" >menu</i>';
    return div;
};
command.addTo(map);
$('.material-icons.md-36.show').hide();

$("#rent_slider").slider({});

$('#rent_slider').slider().on('change', function(event) {

    var a = event.value.newValue;
    var b = event.value.oldValue;

    $("#rent_min").text("€ " + String(a[0]))
    $("#rent_max").text("€ " + String(a[1]))

    var changed = !($.inArray(a[0], b) !== -1 &&
        $.inArray(a[1], b) !== -1 &&
        $.inArray(b[0], a) !== -1 &&
        $.inArray(b[1], a) !== -1 &&
        a.length === b.length);

    if (changed) {
        refresh_markers();
    }
});
$('#check_M').change(function() {
    refresh_markers();
})
$('#check_W').change(function() {
    refresh_markers();
})

$('#check_Flat').change(function() {
    refresh_markers();
})
$('#check_WG').change(function() {
    refresh_markers();
})

$('#transport_select').change(function() {

	reset_all();
})

$('#street_form').change(function() {

	reset_all();
})
$('#zip_form').change(function() {

	reset_all();
})



function reset_all(){

	nr_shown = 0
	json_response = []
	$("#show_wgs").find('span').text('Show WGs!')
	$('#show_wgs').attr('class', 'btn btn-success')
	markerGroup.clearLayers()
	isochroneGroup.clearLayers()

	if ($("select#transport_select").val() == "Public Transport") {
			document.getElementById("show_isos").disabled = true
	} else {
			document.getElementById("show_isos").disabled = false
	}
}


function rent_gender_Filter(feature) {
    if (feature.properties.poi == "true") {
        return true
    }
    var show = false
    var a = $('#rent_slider').slider().val().split(",")
    if (parseInt(a[0]) > feature.properties.rent || feature.properties.rent > parseInt(a[1])) {
        return false
    }

    if ($('#check_M').is(':checked') && (feature.properties.gender == "M" || feature.properties.gender == "MW")) {
        show = true
    }
    if ($('#check_W').is(':checked') && (feature.properties.gender == "W" || feature.properties.gender == "MW")) {
        show = true
    }
    if (show == false) {
        return false
    }

    if ($('#check_Flat').is(':checked') && (feature.properties.type == "Flat")) {
        return true
    }
    if ($('#check_WG').is(':checked') && (feature.properties.type == "WG")) {
        return true
    }


}


function refresh_markers() {
    markerGroup.clearLayers()
    L.geoJson(json_response, {
        filter: rent_gender_Filter,
        onEachFeature: onEachFeature,
        pointToLayer: function(feature, latlng) {
            return L.circleMarker(latlng, style(feature));
        }
    }).addTo(markerGroup);
    markerGroup.addTo(map);
    markerGroup.eachLayer(function(layer) {
        layer.bringToFront()
    });

}

function isochrones_click() {
    isochroneGroup.clearLayers()
    $("#isochrones_icon").toggleClass("fa-circle-o-notch fa-spin")
    $("#show_isos").find('span').text('Loading... ')
    $("#show_isos").prop('disabled', true)

    var city = $("select#city_select").val()
    var address = $("#street_form").val()
    var zip = $("#zip_form").val()
    var transport = $("select#transport_select").val()
    var isochrones = $.ajax({
        type: "POST",
        url: "/isochrones.json",
        dataType: "json",
        contentType: 'application/json',
        data: JSON.stringify({
            "city": city,
            "address": address,
            "zip": zip,
            "transport": transport
        }),
        success: function(response) {
            var polygons = JSON.parse(response).polygons
            for (var i = 0; i < polygons.length; i++) {
                var layer = L.geoJson(polygons[i], {
                    style: {
                        color: 'hsl(' + String(120 - 120 * ((i + 0.5) * 20) / 60) + ',100%,50%)',
                        "fillOpacity": .08 * (polygons.length - i)
                    }
                }).addTo(isochroneGroup);
                layer.bringToBack()

            }
            isochroneGroup.addTo(map);
            markerGroup.eachLayer(function(layer) {
                layer.bringToFront()
            });
                $("#isochrones_icon").toggleClass("fa-circle-o-notch fa-spin")
                $("#show_isos").find('span').text('Show Isochrones!')
                $("#show_isos").prop('disabled', false)
        }
    })

}

function go_click() {


    var city = $("select#city_select").val()
    var address = $("#street_form").val()
    var zip = $("#zip_form").val()
		var update = $.ajax({
				type: "POST",
				url: "/update_poi",
				dataType: "json",
				contentType: 'application/json',
				data: JSON.stringify({
						"city": city,
						"address": address,
						"zip": zip,
				}),
				success: function(response) {
					console.log(response)
					if (response["poi"]=="found")
					{
						$("#wgs_icon").toggleClass("fa-circle-o-notch fa-spin")
						$("#show_wgs").find('span').text('Loading... ')
						$("#show_wgs").prop('disabled', true)
						request_offers()
					}
					else{
						alert("Address not found!");
					}
				}
		})
}


function request_offers(){
		var city = $("select#city_select").val()
    var transport = $("select#transport_select").val()
    var requests = [ ];
    for (var idx = 0; idx < 10; idx++) {
        requests.push($.ajax({
            type: "POST",
            url: "/wgs.json",
            dataType: "json",
            contentType: 'application/json',
            data: JSON.stringify({
                "city": city,
                "transport": transport,
                "idx": idx,
                "nr_shown": json_response.length
            }),
            success: function(response) {
                json_response = json_response.concat(response.features)
                nr_shown += response.features.length
                L.geoJson(response, {
                    filter: rent_gender_Filter,
                    onEachFeature: onEachFeature,
                    pointToLayer: function(feature, latlng) {
                        return L.circleMarker(latlng, style(feature));
                    }
                }).addTo(markerGroup);
                markerGroup.addTo(map)
                markerGroup.eachLayer(function(layer) {
                    layer.bringToFront()
                });
            }
        })
      )
    }
    	$.when.apply( null, requests ).done(function() {
	      $("#wgs_icon").toggleClass("fa-circle-o-notch fa-spin")
	      $("#show_wgs").find('span').text('Show More!')
	      $("#show_wgs").prop('disabled', false)
	      $('#show_wgs').attr('class', 'btn btn-primary')
			});
}


function hide_sidebar() {
    $('.col-md-3').hide();
    $('.material-icons.md-36.show').show();
    $('.col-md-9').addClass('col-md-12').removeClass('col-md-9');
    map.invalidateSize();
}

function show_sidebar() {
    $('.col-md-12').addClass('col-md-9').removeClass('col-md-12');
    $('.col-md-3').show();
    $('.material-icons.md-36.show').hide();
    map.invalidateSize();
}

function onEachFeature(feature, layer) {
    if (feature.properties && feature.properties.poi == "false") {
        layer.bindPopup('<p><a href="' + feature.properties.link + '">Link to wg-gesucht.de </a><br/>Type: ' + feature.properties.type + '<br/>Rent: €' + feature.properties.rent + "<br/>Wanted Gender: " + feature.properties.gender + "<br/>Duration: Approx. " + feature.properties.duration_0 + " Min</p>");
    } else {
        layer.bindPopup("<p>POI</p>")
    }
}

function style(feature) {
    var x = feature.properties.duration_0;

    if (x > 60) {
        x = 60
    } else if (x == 0) {
        return {
            color: 'blue',
            fillOpacity : '0.3'
        }
    }
    return {
        color: 'hsl(' + String(120 - 120 * x / 60) + ',100%,50%)',
        fillOpacity : '0.75'
    };
}
