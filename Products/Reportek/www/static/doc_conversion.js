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
            var result = $("<div id='result'></div>");
            $(result).append(operations_html);
            $('#operations a', result).text('Back to document');
            if(typeof(data)=='string'){
                $(result).append("<pre>{0}</pre>".format(data));
            }
            else{
                $(result).append(data);
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

            /* apply dataTable */
            var errors = $('<div></div>');
            $(errors)
            for(var i=0;i<$('table', result).length;i++){
                try{
                    $($('table', result)[i]).dataTable();
                }catch(e){
                    $(errors).append('<div>'+'table '+ (i+1) +': '+e+'</div>');
                };
            }
            $('div', errors).toggleClass('.warning-msg');
            $(errors).insertAfter('#operations', result);

            $('#pagefoot').hide();
            $('#container').replaceWith(result);
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
