var container_html = '';
var operations_html = '';
var _init = function init(event){
    event.preventDefault();
    trigger_obj = event.target;
    conv_id = trigger_obj.getAttribute('conv_id');
    conv_source = trigger_obj.getAttribute('conv_source');
    conv_file = trigger_obj.getAttribute('conv_file');
    url_string = './ajax_convert?conv={0}&source={1}&file={2}'.format(
                conv_id, conv_source, conv_file)
    $.ajax({
        url: url_string,
        beforeSend: function(){
            var opts = {
              lines: 13, // The number of lines to draw
              length: 10, // The length of each line
              width: 5, // The line thickness
              radius: 30, // The radius of the inner circle
              corners: 1, // Corner roundness (0..1)
              rotate: 0, // The rotation offset
              color: '#000', // #rgb or #rrggbb
              speed: 1, // Rounds per second
              trail: 60, // Afterglow percentage
              shadow: false, // Whether to render a shadow
              hwaccel: false, // Whether to use hardware acceleration
              className: 'spinner', // The CSS class to assign to the spinner
              zIndex: 2e9, // The z-index (defaults to 2000000000)
              top: 'auto', // Top position relative to parent in px
              left: 'auto' // Left position relative to parent in px
            };
            $('#leftcolumn').hide();
            $('#workarea').replaceWith("<div id='spinner' style='min-height: 450px'></div>");
            var target = document.getElementById('spinner');
            var spinner = new Spinner(opts).spin(target);
        },
        success: function(data){
            $('#pagefoot').hide();
            $('#container').replaceWith("<div id='result'></div>");
            $('#result').append(operations_html);
            $('#operations a').text('Back to document');
            if(typeof(data)=='string'){
                $('#result').append("<pre>{0}</pre>".format(data));
            }
            else{
                $('#result').append(data);
            }

            /* make thead from the first row of the table */
            var headless_tables = $('table:not(table:has(thead))');
            var first_rows = $('tr:first-child', headless_tables).remove()
            $(headless_tables).prepend($('<thead></thead>'));
            for(var i=0;i<$(headless_tables).length;i++){
                var first_row = $(first_rows)[i];
                var thead = $('thead', headless_tables)[i];
                $('td > *', first_row).unwrap().wrap('<th>'); /*replace td with th*/
                $(thead).append($(first_row));
            }
            $('table > tbody > tr').removeClass('odd');
            $('table > tbody > tr').removeClass('xx');
            $(headless_tables).dataTable();
            $('pre').css({
                'background-color': 'white',
                'overflow': 'visible'
            });

        },
        statusCode:{
            500: function(data){
                    var result_div = "<div id='result' style='min-height: 450px; text-align: left;'>{0}</div>"
                    var content = "<div style='padding: 210 0 0 0; text-align: center;'>{0}</div>"
                    var message = 'UNABLE TO CONVERT'
                    if(data.getResponseHeader('Content-Type')=='image/png'){
                      message = "<img src='data:image/png;base64,{0}'/>".format(data.responseText);
                    };
                    $('#spinner').replaceWith(result_div.format(content.format(message)));
                    $('#result').prepend(operations_html);
                    $('#operations a').text('Back to document');
                 }
        }
    });
    return false;
}

$(document).ready(function() {
    container_html = $('#container').html();
    operations_html = $('#operations');
    String.prototype.format = function() {
        var args = arguments;
        return this.replace(/{(\d+)}/g, function(match, number) {
            return typeof args[number] != 'undefined' ? args[number] : match ;
        });
    };
    $('body').on('click', '#result #operations a', function(event){
        event.preventDefault();
        $('#result').replaceWith("<div id='container'></div>");
        $('#container').html(container_html);
        $('#pagefoot').show();
        $('#container').on('click', '.converter', _init);
    });

    $('#container').on('click', '.converter', _init);
});
