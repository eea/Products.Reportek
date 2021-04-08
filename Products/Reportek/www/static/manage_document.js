/*global $, jQuery*/
"use strict";
if (window.reportek === undefined) {
    var reportek = {
        version: "1.0"
    };
}

reportek.documents = {
    load: function() {
        var self = reportek.documents;
        self.get_possible_conversions();
        self.get_qa_scripts();
        $("#conversions-reload").on("click", function(evt) {
            evt.preventDefault();
            self.get_possible_conversions();
        });
        $("#qa-reload").on("click", function(evt) {
            evt.preventDefault();
            self.get_qa_scripts();
        });
    },
    get_possible_conversions: function() {
        var self = reportek.documents;
        $("#c_spinner").removeClass("hidden-content");
        $("#c_container").remove();
        $.ajax({
            url: "get_possible_conversions",
            data: {exclude_internal: true},
            success: function(data) {
                self.update_conversions(data);
                $("#c_spinner").addClass("hidden-content");
                $("#conv-status").addClass("hidden-content");
            },
            error: function() {
                $("#c_spinner").addClass("hidden-content");
                $("#conv-status").addClass("hidden-content");
                $(".remote-conversions").text("An error occured while retrieving results. Please try again later!");
            }
        });
    },
    update_conversions: function(data) {
        var self = reportek.documents;
        var conversions = $(".remote-conversions");
        var c_container = $("<div>", {
            id: "c_container"
        });
        if (data.warnings) {
            var caution = $("<a>", {
                class: "caution-msg",
                href: "#",
                text: data.warnings + " Click to reload (additional conversions might be available)"
            });
            caution.on("click", function(evt) {
                evt.preventDefault();
                self.get_possible_conversions();
            });
            c_container.append($("<br>"));
            c_container.append(caution);
        }
        if (data.local_converters.length <= 0 && data.remote_converters.length <= 0) {
            c_container.append($("<p>", {
                text: "No conversions available for this document."
            }));
        }
        var ulist = $("<ul>").appendTo(c_container);
        for (var i = 0; i < data.local_converters.length; i++) {
            var lconv = data.local_converters[i];
            var litem = $("<li>");
            litem.append($("<a>", {
                href: "/Converters/run_conversion?file=" + data.file + "&conv=" + lconv.xsl + "&source=local",
                type: lconv.content_type_out,
                conv_id: lconv.xsl,
                conv_file: data.file,
                conv_source: "local",
                text: lconv.description
            }).append($("<span>"), {
                text: lconv.more_info
            })).appendTo(ulist);
        }
        for (i = 0; i < data.remote_converters.length; i++) {
            var rconv = data.remote_converters[i];
            var ritem = $("<li>");
            ritem.append($("<a>", {
                href: "/Converters/run_conversion?file=" + data.file + "&conv=" + rconv.convert_id + "&source=remote",
                type: rconv.content_type_out,
                text: rconv.description
            }).append($("<span>"), {
                text: rconv.more_info
            })).appendTo(ulist);
        }
        conversions.append(c_container);
    },
    get_qa_scripts: function() {
        var self = reportek.documents;
        $("#qa_container").remove();
        $("#qa_spinner").removeClass("hidden-content");
        $.ajax({
            url: "get_qa_scripts",
            success: function(data) {
                self.update_qa_scripts(data);
                $("#qa_spinner").addClass("hidden-content");
                $("#qa-status").addClass("hidden-content");
            },
            error: function() {
                $("#qa_spinner").addClass("hidden-content");
                $("#qa-status").addClass("hidden-content");
                $(".quality-assessment").text("An error occured while retrieving results. Please try again later!");
            }
        });
    },
    update_qa_scripts: function(data) {
        var q_assessment = $(".quality-assessment");
        var qa_container = $("<div>", {
            id: "qa_container"
        });
        qa_container.appendTo(q_assessment);

        if (data.online_qa.length <= 0 && data.large_qa.length <= 0) {
            qa_container.append($("<p>", {
                text: "No quality assessment scripts available for this document."
            }));
        }
        for (var i = 0; i < data.online_qa.length; i++) {
            var o_qa_entry = $("<p>");
            var idx = i + 1;
            o_qa_entry.append($("<span>", {
                text: "Run " + data.online_qa[i].title + " "
            }));
            o_qa_entry.append($("<a>", {
                href: "runQAScript?p_file_url=" + data.file + "&p_script_id=" + data.online_qa[i].script_id,
                title: "Click to run " + data.online_qa[i].title,
                rel: "nofollow",
                class: "test_button",
                text: "Run QA #" + idx
            }));
            o_qa_entry.appendTo(q_assessment);
        }
        for (i = 0; i < data.large_qa.length; i++) {
            $("<p>", {
                text: "File too large to run the <em>" + data.large_qa[i].title + "</em> quality assessment script directly. Use the feedback generated by the <em>automatic quality assessment</em> to view the results.",
            }).appendTo(qa_container);
        }
    }
};
jQuery(document).ready(function() {
    reportek.documents.load();
});
