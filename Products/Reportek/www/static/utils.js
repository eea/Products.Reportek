function activate_tab(){
    document.getElementById(arguments[0]).style.display = "block";
    for (var idx = 1; idx < arguments.length; idx++) {
        document.getElementById(arguments[idx]).style.display= "none";
    }
}
