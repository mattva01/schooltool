$(document).ready(function() {
    // accordion setup
    $( ".person-info" ).accordion({
        header: 'h2',
        collapsible: true,
        autoHeight: false,
    });
});

function call_dialog(url, form_id) {
    $(form_id).load(url).hide();
    $(form_id).dialog({
        autoOpen: false,
        modal: true,
        resizable: false,
        draggable: false,
        width: $(form_id).find('form').width() + 30
    });
    $(form_id).dialog('open');
}

