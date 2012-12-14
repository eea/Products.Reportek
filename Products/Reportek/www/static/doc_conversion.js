var container_html = '';
var operations_html = '';
var _init = function init(event){
    event.preventDefault();
    trigger_obj = event.target;
    conv_id = trigger_obj.getAttribute('conv_id');
    conv_source = trigger_obj.getAttribute('conv_source');
    conv_file = trigger_obj.getAttribute('conv_file');
    url_string = '/Converters/run_conversion?conv={0}&source={1}&file_url={2}&ajax_call=1'.format(
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
            var result = $("<div id='result'></div>");
            $(result).append(operations_html);
            $('#operations a', result).text('Back to document');
            if(data.mime_type=='text/plain'){
                $(result).append("<pre>{0}</pre>".format(data.content));
            }
            else{
                if(data.mime_type == 'image/png'){
                    $(result).append(
                        "<img src='data:{0};base64,{1}'/>".format(data.mime_type, data.content)
                    );
                }
                else{
                    $(result).append(data.content);
                }
            }
            $('pre', result).css({
                'background-color': 'white',
                'overflow': 'visible'
            });


            var headless_tables = $('table:not(table:has(thead))', result);
            var first_rows = $('tr:first-child', headless_tables).remove()

            /* create a thead for tables without one */
            $(headless_tables).prepend($('<thead></thead>'));
            /* move first row to thead and replace td's with th's */
            for(var i=0;i<$(headless_tables).length;i++){
                var length_diff=0;
                var first_row = $(first_rows[i]);
                var second_row = $('tr:first-child', headless_tables[i]);
                var thead = $('thead', headless_tables)[i];
                try{
                    length_diff = ($('td', first_row).length - $('td', second_row).length);
                }catch(e){
                    /* probably second_row was undefined */
                    /* leave length_diff 0 */
                }
                if(length_diff>0){
                    for(var j=0;j<length_diff;j++){
                        $('tr', headless_tables[i]).append('<td></td>');
                    }
                }
                $('td', first_row).wrapInner('<th>');
                $('td th', first_row).unwrap();
                $(thead).append($(first_row));
            }
            $('table > tbody > tr', result).removeClass('odd');
            $('table > tbody > tr', result).removeClass('xx');

            tables = $('table', result);
            var i=0;
            $('table', result).replaceWith(function(){
                var placeholder = $('<div class="placeholder" id="ph{0}"></div>'.format(i));
                i++;
                return $(placeholder)
            });
            $(result).insertAfter('#operations', result);

            $('#pagefoot').hide();
            var img = $("<img />").attr('src', '++resource++static/ajax-loader.gif');
            $('.placeholder', result).html(img);
            $('#container').replaceWith($(result));
            info = $('<div>')
            function dT(i){
                if(i>=tables.length){
                    return false;
                }
                table = $(tables[i]).wrap('<div/>');//.dataTable()
                $('#result #ph{0}'.format(i)).replaceWith(table);
                var p_info = $('<p>')
                var p_warn = $('<p>')
                try{
                    $(info).append(
                        $(p_info).text(
                            'INFO: Formatting table {0}.'.format(i+1)
                        )
                    );
                    $(table).dataTable();
                    window.setTimeout(function(){
                        $(p_info).append(' Done.');
                    }, 0);
                }catch(err){
                    $(info).append(
                        $(p_warn).text(
                            'WARNING: Table {0} cannot be displayed as data table.'.format(i+1)
                        )
                    );
                }
                window.setTimeout(function(){
                    $(p_info).fadeOut();
                }, 3000);
                window.setTimeout(function(){
                    $(p_warn).fadeOut();
                }, 6000);
                i++;
                window.setTimeout(function(){dT(i);}, 0);
            }
            var i=0;
            dT(i);
            $(info).insertAfter($(operations));
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
