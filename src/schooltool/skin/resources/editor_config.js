CKEDITOR.editorConfig = function( config )
{
    config.toolbar = [
      ['Bold','Italic','RemoveFormat'], // ,'Underline','Strike','-','Subscript','Superscript'
      ['Cut','Copy','PasteText'], // ,'Paste','PasteFromWord','-','Undo','Redo'
      //['NumberedList','BulletedList','-','Outdent','Indent']
      //['JustifyLeft','JustifyCenter','JustifyRight','JustifyBlock'],
      ['Link'] // ,'Unlink','Anchor'],
      //['Styles','Format','Font','FontSize'],
      //['TextColor','BGColor'],
    ];

    config.removeDialogTabs = 'link:target;link:advanced';
    config.removePlugins = 'colorbutton,colordialog,elementspath,flash,newpage,resizer,stylescombo';
    config.toolbarCanCollapse = false;

    config.forcePasteAsPlainText = true;
    config.entities = false;
    config.entities_latin = false;
    config.entities_greek = false;
};
