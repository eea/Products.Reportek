/*global $, jQuery*/
/*global document*/
/*global window*/
/*jslint browser:true */
/* jslint:disable */
function confirm_cancel(e) {
    if (!confirm("Are you sure you want to cancel the current activity and move back to the previous manual activity?")) {
      e.preventDefault();
    }
}

function count_occurence(string, word) {
    var stringLC = string.toLowerCase();
    var wordLC = word.toLowerCase();

    var count = stringLC.split(wordLC).length - 1;

    return count;
}

function get_filtered_entries(items) {
    var results = [];
    items.forEach(function (item, idx, array) {
        if (item.event.indexOf('arrival') == -1 &&
        item.event.indexOf('assigned') == -1 &&
        item.event.indexOf('active') == -1 &&
        item.event.indexOf('creation') == -1 &&
        item.event !== 'complete' &&
        item.event.indexOf('assigned') == -1) {
            results.push(item);
        }
    });
    return results;
}

function should_poll() {
    var status = $(".dynamic-status");
    if (!status.hasClass("manual") && !status.hasClass("env-completed") && !status.hasClass("inactive")) {
        return true;
    }
    return false;
}

function pollServer() {
    if ($(".overview-status").length > 0 && should_poll()) {
        window.setTimeout(get_wk_metadata, 10000);
    }
}

function get_wk_metadata() {
    var wk_id = $(".overview-status").attr("data-workitem");

    $.ajax({
        url: "get_wk_metadata?workitem_id=" + wk_id,
        type: "GET",
        success: function (result) {
            if (result.history.length > 0) {
                var act_type = result.activity_type;
                var valid_items = get_filtered_entries(result.history);
                var failed_qa = result.failure;
                if (failed_qa && !$(".dynamic-status").hasClass("qa-failure")) {
                    if ($(".dynamic-status").hasClass("active")) {
                        $(".dynamic-status").removeClass("active");
                        $(".dynamic-status").addClass("qa-failure");
                    }
                }
                var sl = $(".status-logs");
                var sl_header = $(".status-logs-head");
                var sl_footer = $(".status-logs-footer");
                var tc = $(sl_header).find('p');
                var total_jobs = 0;
                var finished_jobs = 0;
                if (tc.length <= 0) {
                    tc = $("<p>", {
                        'text': 'Task start time: ' + new Date(result.history[0].time).toLocaleString(),
                        'class': 'sl-header-entry'
                    });
                    sl_header.append(tc);
                }
                $(".status-logs div").remove();
                if (act_type === 'automatic') {
                    valid_items.forEach(function (item, idx, array) {
                        if (item.event.indexOf('progress') !== -1) {
                            total_jobs += count_occurence(item.event, '#');
                        }
                        if (item.event.indexOf('completed') !== -1) {
                            finished_jobs += count_occurence(item.event, '#');
                        }
                        if (total_jobs > 0) {
                            $("#progress_info").text(finished_jobs + " out of " + total_jobs + " QA checks completed");
                        }
                        var result = $("<div>", {
                            'class': 'status-log-entry',
                            'text': new Date(item.time).toLocaleString() + ' - '
                        });
                        result.append($.parseHTML(item.event));
                        if (idx === array.length - 1){
                            result.addClass("last-entry");
                            if (!sl.hasClass("hidden-content")) {
                                sl.append(result);
                            } else {
                                sl_footer.empty();
                                sl_footer.append(result);
                            }
                        } else {
                            sl.append(result);
                        }
                        if (($(".status-log-entry").length >= 2 || $(".cancel-activity.status-control").length > 0)) {
                            if($("#status-controls").hasClass("hidden-content")) {
                                $("#status-controls").removeClass("hidden-content");
                            }
                            $("#toggle_history_label").removeClass("hidden-content");
                            if ($(".cancel-activity.status-control").length > 0 && $(".status-log-entry").length < 2) {
                                $("#toggle_history_label").addClass("hidden-content");
                            }
                        }
                        if (item.event.indexOf('forwarded to') !== -1) {
                            window.location.reload();
                        }
                    });
                } else {
                    if ($(".dynamic-status").hasClass("active")) {
                        $(".ds-loader").remove();
                        $(".dynamic-status").addClass("manual");
                    }
                }
                if ($(".status-logs-footer").children().length <= 0 && $(".status-logs").hasClass("hidden-content")) {
                    $(".status-logs-head").removeClass("border-bottom-dotted");
                    $(".status-logs-footer").removeClass("margin-tb-added");
                }
                sl.scrollTop(sl[0].scrollHeight);
            }
            pollServer();
        },
        error: function () {
            //ERROR HANDLING
            pollServer();
        }});
}

function toggle_btn(label) {
    var _for = label.getAttribute('for');
    var _toggleID = 'input#'+_for;
    var hist_toggle = $(_toggleID);
    var isChecked = !hist_toggle.is(':checked');
    var sl_footer = $(".status-logs-footer");
    var sl = $(".status-logs");

    if (isChecked) {
        sl.append($(".status-log-entry.last-entry"));
        sl_footer.children().remove();
        $(".status-logs").removeClass("hidden-content");
        $(".status-logs-footer").removeClass("margin-top-added");
    } else {
        sl_footer.append($(".status-log-entry.last-entry"));
        sl.remove($(".status-log-entry.last-entry"));
        $(".status-logs").addClass("hidden-content");
        $(".status-logs-footer").addClass("margin-top-added");
    }
}
$().ready(function () {
    if (should_poll()) {
        get_wk_metadata();
    }
    $("#toggle_history_label").click(function () {
        toggle_btn(this);
    });
});


