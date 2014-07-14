function activate_tab() {
    /*
     * Implements the tab switching mechanism for 'tabbedmenu'
     * Receives variable number of arguments.
     * First argument is the id of the div how should be visible.
     * The following are the div's id how should be hidden.
     */
    if (arguments.length < 1)
        return;
    document.getElementById(arguments[0]).style.display = "block";
    for (var idx = 1; idx < arguments.length; idx++) {
        document.getElementById(arguments[idx]).style.display= "none";
    }
    /*
     * Than switch the tabs
     */ 
    switch_tabs();
}

function switch_tabs() {
    /*
     * TODO: make it more general
     */
    crtab = document.getElementById('currenttab');
    next = document.getElementById('next');
    crtab.removeAttribute("id");
    next.setAttribute("id", 'currenttab');

    /* remove ancor */
    next.childNodes[1].childNodes[1].remove();
    span_text = document.createTextNode("Grouped by person");
    next.childNodes[1].appendChild(span_text);

    /* add ancor */
    ancor_text = document.createTextNode("Grouped by path");
    ancor = document.createElement("a");
    ancor.appendChild(ancor_text);
    crtab.childNodes[1].remove();
    crtab.appendChild(ancor);
}
