import React, { useState, useCallback } from 'react';
import { Download, FileText, Loader2, AlertCircle, RefreshCw, FileDown, BookOpen } from 'lucide-react';
import { Button } from '../ui/button';
import { toast } from 'sonner';
import { trackEvent } from '../../utils/analytics';
import api from '../../utils/api';

/**
 * PDF button states:
 *   idle      → "Download PDF" (clickable)
 *   loading   → "Preparing PDF..." (spinner, disabled)
 *   error     → "PDF unavailable, try again" (retry)
 */

export function ComicDownloads({
  jobId,
  uiState,          // READY | PARTIAL_READY | VALIDATING | FAILED
  downloadReady,
  hasPanels,
  onDownloadPng,
  onDownloadScript,
  downloading,
}) {
  const [pdfState, setPdfState] = useState('idle'); // idle | loading | error
  const [bookState, setBookState] = useState('idle'); // idle | loading | error

  const handlePdfDownload = useCallback(async () => {
    if (!jobId || pdfState === 'loading') return;
    setPdfState('loading');
    trackEvent('comic_pdf_download_click', { job_id: jobId });

    try {
      const res = await api.get(`/api/photo-to-comic/pdf/${jobId}`, {
        responseType: 'blob',
        timeout: 60000,
      });

      if (res.status === 200 && res.data) {
        const blob = new Blob([res.data], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `comic_${jobId.slice(0, 8)}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast.success('PDF downloaded!');
        setPdfState('idle');
        trackEvent('comic_pdf_download_success', { job_id: jobId });
      } else {
        throw new Error('Empty response');
      }
    } catch (err) {
      const status = err.response?.status;
      if (status === 404) {
        toast.error('Comic not found');
      } else if (status === 400) {
        toast.error('No panels ready for PDF export');
      } else {
        toast.error('PDF generation failed. Try again.');
      }
      setPdfState('error');
      trackEvent('comic_pdf_download_fail', { job_id: jobId, status });
    }
  }, [jobId, pdfState]);

  const handleComicBookDownload = useCallback(async () => {
    if (!jobId || bookState === 'loading') return;
    setBookState('loading');
    trackEvent('comic_book_download_click', { job_id: jobId });

    try {
      const res = await api.get(`/api/photo-to-comic/comic-book/${jobId}`, {
        responseType: 'blob',
        timeout: 90000,
      });

      if (res.status === 200 && res.data) {
        const blob = new Blob([res.data], { type: 'application/pdf' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `comic_book_${jobId.slice(0, 8)}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast.success('Comic Book downloaded!');
        setBookState('idle');
        trackEvent('comic_book_download_success', { job_id: jobId });
      } else {
        throw new Error('Empty response');
      }
    } catch (err) {
      const status = err.response?.status;
      toast.error(status === 400 ? 'No panels ready for comic book' : 'Comic book generation failed. Try again.');
      setBookState('error');
      trackEvent('comic_book_download_fail', { job_id: jobId, status });
    }
  }, [jobId, bookState]);

  const handlePngClick = useCallback(() => {
    trackEvent('comic_png_download_click', { job_id: jobId });
    onDownloadPng();
  }, [jobId, onDownloadPng]);

  const handleScriptClick = useCallback(() => {
    trackEvent('comic_script_download_click', { job_id: jobId });
    onDownloadScript();
  }, [jobId, onDownloadScript]);

  const isReady = uiState === 'READY' || uiState === 'PARTIAL_READY';
  const showPdf = isReady && downloadReady;
  const showScript = isReady && downloadReady && hasPanels;
  const showComicBook = isReady && downloadReady && hasPanels;

  const renderStateButton = (state, onClickFn, idleLabel, loadingLabel, errorLabel, icon, testId, variant = 'outline') => (
    <Button
      onClick={onClickFn}
      disabled={state === 'loading'}
      variant={state === 'error' ? 'destructive' : variant}
      className={`w-full text-sm ${
        state === 'error'
          ? 'border-red-500/40 text-red-400 hover:bg-red-500/10'
          : 'border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800'
      }`}
      data-testid={testId}
    >
      {state === 'loading' ? (
        <><Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />{loadingLabel}</>
      ) : state === 'error' ? (
        <><RefreshCw className="w-3.5 h-3.5 mr-1.5" />{errorLabel}</>
      ) : (
        <>{icon}{idleLabel}</>
      )}
    </Button>
  );

  return (
    <div className="space-y-3" data-testid="comic-downloads">
      {/* Trust copy */}
      {isReady && (
        <p className="text-xs text-slate-400 text-center" data-testid="download-trust-copy">
          Your comic is ready. Download it as PNG, script, PDF, or comic book.
        </p>
      )}

      {/* PNG Download */}
      <Button
        onClick={handlePngClick}
        disabled={downloading || !downloadReady}
        className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 py-4"
        data-testid="download-png-btn"
      >
        {downloading ? (
          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
        ) : (
          <Download className="w-4 h-4 mr-2" />
        )}
        {downloading
          ? 'Downloading...'
          : !downloadReady
            ? uiState === 'VALIDATING' ? 'Verifying...' : 'Unavailable'
            : 'Download PNG'}
      </Button>

      {/* PDF Download */}
      {showPdf && renderStateButton(
        pdfState, handlePdfDownload,
        'Download PDF', 'Preparing PDF...', 'PDF unavailable, try again',
        <FileDown className="w-3.5 h-3.5 mr-1.5" />,
        'download-pdf-btn'
      )}

      {/* Script Download */}
      {showScript && (
        <Button
          variant="outline"
          onClick={handleScriptClick}
          className="w-full border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800 text-sm"
          data-testid="download-script-btn"
        >
          <FileText className="w-3.5 h-3.5 mr-1.5" /> Download Story Script
        </Button>
      )}

      {/* Comic Book Download */}
      {showComicBook && renderStateButton(
        bookState, handleComicBookDownload,
        'Download Comic Book', 'Building Comic Book...', 'Comic book failed, try again',
        <BookOpen className="w-3.5 h-3.5 mr-1.5" />,
        'download-comic-book-btn'
      )}
    </div>
  );
}
