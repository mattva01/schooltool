
// Base path screws up editor for sites using mod rewrite, like
// http://example.com/something/schoooltool/...
// See https://bugs.edge.launchpad.net/schooltool/+bug/258951
//FCKConfig.BasePath = '/@@/fckeditor/editor/';

FCKConfig.EditorAreaCSS = '/@@/schooltool.skin.flourish-fckeditor/fck_editorarea.css';
FCKConfig.CustomConfigurationsPath = "/@@/zope_fckconfig.js";
FCKConfig.SkinPath = '/@@/schooltool.skin.flourish-fckeditor/';

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
FCKConfig.LinkUpload = false ;
FCKConfig.LinkDlgHideAdvanced = true;
FCKConfig.LinkDlgHideTarget = true ;

FCKConfig.ImageBrowser = false ;

FCKConfig.ForcePasteAsPlainText = true ;
// Once we update to CK editor 3.x, figure out a good combination of these
// and maybe re-enable paste from Word
//FCKConfig.pasteFromWordRemoveFontStyles
//FCKConfig.pasteFromWordRemoveStyles
