# backend/portal/pdf_utils.py

from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa   # pastikan sudah: pip install xhtml2pdf

def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)

    response = HttpResponse(content_type="application/pdf")
    # boleh diubah jadi attachment kalau mau langsung download:
    # response["Content-Disposition"] = 'attachment; filename="penilaian_seminar.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse("Terjadi error saat generate PDF", status=500)
    return response
