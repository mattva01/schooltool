FCKConfig.BasePath = '/@@/fckeditor/editor/';
FCKConfig.EditorAreaCSS = FCKConfig.BasePath + 'css/fck_editorarea.css' ;
FCKConfig.CustomConfigurationsPath = "/@@/zope_fckconfig.js";

FCKConfig.ToolbarSets["schooltool"] = [
  ['Bold','Italic','RemoveFormat'], // 'Underline','StrikeThrough','-','Subscript','Superscript'
  //['Source'],
  ['Cut','Copy','PasteText'], // ,'Paste','PasteWord'],
  // ['SelectAll'], // , // for IE JS, unlike Python, never end a list with a comma!
  //['OrderedList','UnorderedList','-','Outdent','Indent'],
  //['JustifyLeft','JustifyCenter','JustifyRight','JustifyFull'],
  //['Image','Link','Unlink','Anchor','Table','Rule'],
  ['Link']
  //'/',
  //['Style','FontFormat','FontName','FontSize'],
  //['TextColor','BGColor'],
  //['About']
  ];

// set faked table borders on table with border="0"
FCKConfig.ShowBorders   = true ;

// The contextURL is set in the javascript template and used in the explorer
// implementation
FCKConfig.contextURL = window.top.top.contextURL;

FCKConfig.LinkBrowser = false ;

FCKConfig.ImageBrowser = false ;
