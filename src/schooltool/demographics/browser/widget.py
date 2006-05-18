from zope.app.form.browser import DateWidget as DateWidget_
from zope.app.form.browser.widget import renderElement
from zope.app import zapi
from zope.app.component.hooks import getSite

class FancyDateWidget(DateWidget_):
    def __call__(self):
        result = super(FancyDateWidget, self).__call__()
        site_url = zapi.absoluteURL(getSite(), self.request)
        img_tag = renderElement(
            "img",
            cssClass="CalIcon",
            src=site_url + "/@@/calwidget-icon.gif",
            id=self.name + "Icon",
            onmousedown="",
            alt="[popup calendar]",
            onclick="clickWidgetIcon('%s');" % self.name)
        div_tag = renderElement(
            "div",
            id=self.name + "Div",
            style="background: #fff; position: absolute; display: none;")
        return result + img_tag + div_tag
