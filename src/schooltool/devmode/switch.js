function switchDisplay(id) {

    if(document.getElementById) {
       // DOM
       var element = document.getElementById(id);
    } else {
        if(document.all) {
            // Proprietary DOM
            var element = document.all[id];
        } else {
            // Create an object to prevent errors further on
            var element = new Object();
        }
    }

    if(!element) {
        /* The page has not loaded or the browser claims to support
        document.getElementById or document.all but cannot actually
        use either */
        return;
    }

    // Reference the style ...
    if (element.style) { 
        style = element.style;
    }

    if (typeof(style.display) == 'undefined' &&
        !( window.ScriptEngine && ScriptEngine().indexOf('InScript') + 1 ) ) {
        //The browser does not allow us to change the display style
        //Alert something sensible (not what I have here ...)
        window.alert( 'Your browser does not support this' );
        return;
    }

    // Change the display style
    if (style.display == 'none') {
        style.display = '';
        switchImage(id, 'varrow.png'); 
   }
    else {
        style.display = 'none'
        switchImage(id, 'harrow.png'); 
    }
}

function switchImage(id, name) {
    if(document.getElementById) {
       // DOM
       var element = document.getElementById(id+'.arrow');
    } else {
       // Proprietary DOM
       var element = document.all[id+'.arrow'];
    }
    element.src = '/@@/'+name;
}