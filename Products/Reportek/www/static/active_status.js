/*global $, jQuery*/
/*global document*/
/*global window*/
/*jslint browser:true */
/* jslint:disable */

function get_wk_history() {
    var wk_id = $(".overview-status-active").attr("data-workitem");

    $.ajax({
        url: "get_wk_history?workitem_id=" + wk_id,
        type: "GET",
        success: function (items) {
            if (items.length > 0) {
                var status_logs = $(".status-logs");
                $(".status-logs div").empty();
                items.forEach((item) => {
                    var result = $("<div>", {
                        class: 'status-log-entry',
                        text: new Date(item.time).toLocaleString() + ' - '
                    });
                    result.append($.parseHTML(item.event));
                    status_logs.append(result);
                    if (item.event.indexOf('forwarded to') !== -1) {
                        window.location.reload();
                    }
                  });
                //   $(".overview-status-active").html(result);
                var stage = $("<div>", {
                    class: 'stage'
                });
                var dot = $("<div>", {
                    class: 'dot-pulse'
                });
                stage.append(dot);
                $(".status-log-entry:last").append(stage);
                status_logs.scrollTop(status_logs[0].scrollHeight);
            }
            pollServer();
        },
        error: function () {
            //ERROR HANDLING
            pollServer();
        }});
}

function pollServer() {
    if ($(".overview-status-active").length > 0)
    {
        window.setTimeout(get_wk_history, 10000);
    }
}

$().ready(function () {
    get_wk_history();
});


