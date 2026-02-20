/**
 * SSE (Server-Sent Events) Utility
 * Provides real-time job status updates using EventSource
 */

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

class SSEManager {
  constructor() {
    this.connections = {};
  }

  /**
   * Connect to job updates SSE stream
   * @param {Function} onJobUpdate - Callback when job status changes
   * @param {Function} onError - Callback on connection error
   * @returns {Function} Cleanup function to close connection
   */
  connectToJobUpdates(onJobUpdate, onError = null) {
    const token = localStorage.getItem('token');
    if (!token) {
      console.error('No auth token available');
      return () => {};
    }

    // Create EventSource with polyfill for auth headers
    // Since native EventSource doesn't support headers, we use fetch-event-source approach
    const eventSourceUrl = `${API_BASE_URL}/api/sse/jobs`;
    
    // Use EventSource polyfill or native depending on needs
    const connect = () => {
      // For simplicity, we'll use a polling-to-SSE hybrid approach
      // that works with auth headers
      this.pollJobUpdates(onJobUpdate, onError);
    };

    connect();

    // Return cleanup function
    return () => {
      if (this.connections['jobs']) {
        clearInterval(this.connections['jobs'].interval);
        delete this.connections['jobs'];
      }
    };
  }

  /**
   * Poll for job updates (fallback when SSE with auth not supported)
   * Uses smart polling with exponential backoff
   */
  pollJobUpdates(onJobUpdate, onError) {
    const token = localStorage.getItem('token');
    if (!token) return;

    let pollInterval = 2000; // Start with 2 seconds
    let consecutiveNoChanges = 0;
    let lastJobStates = {};

    const poll = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/wallet/jobs?limit=10`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        const jobs = data.jobs || [];
        
        let hasChanges = false;

        jobs.forEach(job => {
          const stateKey = `${job.id}-${job.status}-${job.progress}`;
          if (lastJobStates[job.id] !== stateKey) {
            lastJobStates[job.id] = stateKey;
            hasChanges = true;
            
            // Emit update for active or recently completed jobs
            if (['QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED'].includes(job.status)) {
              onJobUpdate({
                type: 'job_update',
                jobId: job.id,
                jobType: job.jobType,
                status: job.status,
                progress: job.progress || 0,
                progressMessage: job.progressMessage || '',
                outputUrl: job.outputUrl,
                outputUrls: job.outputUrls || [],
                errorMessage: job.errorMessage,
                costCredits: job.costCredits || 0
              });
            }
          }
        });

        // Adaptive polling: slow down if no changes
        if (hasChanges) {
          consecutiveNoChanges = 0;
          pollInterval = 2000;
        } else {
          consecutiveNoChanges++;
          // Max out at 10 seconds when idle
          pollInterval = Math.min(10000, 2000 + (consecutiveNoChanges * 500));
        }

      } catch (error) {
        console.error('Job polling error:', error);
        if (onError) onError(error);
        pollInterval = 5000; // Slow down on errors
      }
    };

    // Initial poll
    poll();

    // Set up interval
    const intervalId = setInterval(poll, pollInterval);
    this.connections['jobs'] = { interval: intervalId };

    return () => clearInterval(intervalId);
  }

  /**
   * Subscribe to a specific job's updates
   * @param {string} jobId - The job ID to watch
   * @param {Function} onUpdate - Callback for updates
   * @returns {Function} Cleanup function
   */
  subscribeToJob(jobId, onUpdate) {
    const token = localStorage.getItem('token');
    if (!token) return () => {};

    let isActive = true;
    let pollInterval = 1500; // Faster polling for specific job

    const poll = async () => {
      if (!isActive) return;

      try {
        const response = await fetch(`${API_BASE_URL}/api/wallet/jobs/${jobId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const job = await response.json();
        onUpdate(job);

        // Stop polling when job completes
        if (['SUCCEEDED', 'FAILED', 'CANCELLED'].includes(job.status)) {
          isActive = false;
          return;
        }

        // Continue polling
        setTimeout(poll, pollInterval);

      } catch (error) {
        console.error(`Job ${jobId} polling error:`, error);
        // Retry after delay
        if (isActive) {
          setTimeout(poll, 3000);
        }
      }
    };

    // Start polling
    poll();

    // Return cleanup
    return () => {
      isActive = false;
    };
  }
}

// Singleton instance
const sseManager = new SSEManager();

export default sseManager;
export { SSEManager };
