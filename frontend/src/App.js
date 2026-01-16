import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  // Order: JSON, TOON, YAML, CSV
  const [formats, setFormats] = useState({
    json: '',
    toon: '',
    yaml: '',
    csv: ''
  });
  
  const [tokenCounts, setTokenCounts] = useState({
    toon: 0,
    json: 0,
    yaml: 0,
    csv: 0
  });
  const [activeFormat, setActiveFormat] = useState(null);
  const [error, setError] = useState('');
  const [formatWarning, setFormatWarning] = useState(null);
  const [loading, setLoading] = useState(false);
  const debounceTimer = useRef(null);

  // Auto-convert when content changes
  useEffect(() => {
    if (!activeFormat) return;
    
    const content = formats[activeFormat];
    if (!content.trim()) {
      // Clear other formats if active format is cleared
      setFormats({
        json: '',
        toon: '',
        yaml: '',
        csv: ''
      });
      setTokenCounts({
        json: 0,
        toon: 0,
        yaml: 0,
        csv: 0
      });
      setError('');
      return;
    }

    // Debounce API calls
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    debounceTimer.current = setTimeout(async () => {
      await convertFormat(content, activeFormat);
    }, 500); // 500ms debounce

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [formats[activeFormat], activeFormat]);

  const convertFormat = async (content, fromFormat) => {
    if (!content.trim()) return;

    setLoading(true);
    setError('');

    try {
      const response = await axios.post('/api/convert', {
        content: content,
        from_format: fromFormat
      }, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.data.success) {
        // Update all formats except the active one
        setFormats(prev => ({
          ...prev,
          json: response.data.json || prev.json,
          toon: response.data.toon || prev.toon,
          csv: response.data.csv || prev.csv,
          yaml: response.data.yaml || prev.yaml
        }));
        
        // Update token counts
        if (response.data.tokens) {
          setTokenCounts(response.data.tokens);
        }
        
        // Handle format warning - show even if conversion succeeded
        if (response.data.format_warning) {
          setFormatWarning(response.data.format_warning);
          // Clear error if we have a format warning (warning is more helpful)
          setError('');
        } else {
          setFormatWarning(null);
        }
      } else {
        // Check if error response has format_warning
        if (response.data.format_warning) {
          setFormatWarning(response.data.format_warning);
          // Clear error - warning is more helpful
          setError('');
        } else {
          setError(response.data.error || 'Conversion failed');
          setFormatWarning(null);
        }
      }
    } catch (err) {
      // Check if error response has format_warning
      if (err.response?.data?.format_warning) {
        setFormatWarning(err.response.data.format_warning);
        // Clear error - warning is more helpful
        setError('');
      } else {
        setError(err.response?.data?.error || 'Failed to convert');
        setFormatWarning(null);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (format, value) => {
    setActiveFormat(format);
    setFormats(prev => ({
      ...prev,
      [format]: value
    }));
  };

  const handleDownload = (format, content) => {
    if (!content) return;

    const extensions = {
      json: 'json',
      toon: 'toon',
      csv: 'csv',
      yaml: 'yaml'
    };

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `output.${extensions[format]}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleClear = () => {
    setFormats({
      toon: '',
      json: '',
      yaml: '',
      csv: ''
    });
    setTokenCounts({
      toon: 0,
      json: 0,
      yaml: 0,
      csv: 0
    });
    setActiveFormat(null);
    setError('');
    setFormatWarning(null);
  };
  
  const handleSwitchToCorrectFormat = (detectedFormat) => {
    if (!activeFormat) return;
    
    // Get content from current box
    const content = formats[activeFormat];
    
    // Clear current format
    setFormats(prev => ({
      ...prev,
      [activeFormat]: ''
    }));
    
    // Set content in correct format box
    setFormats(prev => ({
      ...prev,
      [detectedFormat]: content
    }));
    
    // Switch active format
    setActiveFormat(detectedFormat);
    setFormatWarning(null);
    
    // Trigger conversion
    setTimeout(() => {
      convertFormat(content, detectedFormat);
    }, 100);
  };

  const formatLabels = {
    json: 'JSON',
    toon: 'TOON',
    csv: 'CSV',
    yaml: 'YAML'
  };

  const formatPlaceholders = {
    json: '{\n  "name": "John",\n  "age": 30\n}',
    toon: 'name:John\nage:30',
    csv: 'name,age\nJohn,30',
    yaml: 'name: John\nage: 30'
  };

  // Order: JSON, TOON, YAML, CSV
  const formatOrder = ['json', 'toon', 'yaml', 'csv'];

  return (
    <div className="App">
      <div className="container">
        <header className="header">
          <h1>Data Format Converter</h1>
          <p>Multi-format data conversion and token optimization tool</p>
          <p className="subtitle">Paste content into any format box to automatically convert to all other formats</p>
        </header>

        {formatWarning && (
          <div className="format-warning-banner">
            <div className="warning-content">
              <span className="warning-icon">⚠</span>
              <span className="warning-message">{formatWarning.message}</span>
              <button
                onClick={() => handleSwitchToCorrectFormat(formatWarning.detected_format)}
                className="switch-format-btn"
              >
                Switch to {formatLabels[formatWarning.detected_format]} Box
              </button>
            </div>
          </div>
        )}

        {error && !formatWarning && (
          <div className="error-banner">
            {error}
          </div>
        )}

        <div className="formats-grid">
          {formatOrder.map((format) => (
            <div key={format} className={`format-box ${activeFormat === format ? 'active' : ''}`}>
              <div className="format-header">
                <h3>{formatLabels[format]}</h3>
                <div className="format-actions">
                  {formats[format] && (
                    <button
                      onClick={() => handleDownload(format, formats[format])}
                      className="action-btn"
                      title="Download"
                    >
                      Download
                    </button>
                  )}
                  {formats[format] && (
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(formats[format]);
                      }}
                      className="action-btn"
                      title="Copy"
                    >
                      Copy
                    </button>
                  )}
                </div>
              </div>
              <textarea
                value={formats[format]}
                onChange={(e) => handleInputChange(format, e.target.value)}
                placeholder={formatPlaceholders[format]}
                className={`format-input ${formats[format] ? 'has-content' : ''}`}
                disabled={loading && activeFormat !== format}
              />
              {loading && activeFormat === format && (
                <div className="loading-indicator">Converting...</div>
              )}
              <div className="token-count">
                <span className="token-label">Tokens:</span>
                <span className="token-value">
                  {tokenCounts[format] > 0 ? tokenCounts[format].toLocaleString() : '-'}
                </span>
              </div>
            </div>
          ))}
        </div>

        {Object.values(tokenCounts).some(count => count > 0) && (
          <div className="token-summary">
            <div className="token-summary-header">
              <h3>Token Summary (Descending Order)</h3>
              <button
                onClick={() => {
                  const summaryText = Object.entries(tokenCounts)
                    .filter(([_, count]) => count > 0)
                    .sort(([_, a], [__, b]) => b - a)
                    .map(([format, count]) => `${formatLabels[format]}: ${count.toLocaleString()} tokens`)
                    .join('\n');
                  navigator.clipboard.writeText(summaryText);
                }}
                className="action-btn copy-summary-btn"
                title="Copy Summary"
              >
                Copy Summary
              </button>
            </div>
            <div className="token-list">
              {Object.entries(tokenCounts)
                .filter(([_, count]) => count > 0)
                .sort(([_, a], [__, b]) => b - a)
                .map(([format, count], index, array) => {
                  const isLowest = index === array.length - 1;
                  return (
                    <div key={format} className={`token-summary-item ${isLowest ? 'lowest' : ''}`}>
                      <span className="token-format-name">{formatLabels[format]}:</span>
                      <span className="token-format-count">{count.toLocaleString()} tokens</span>
                    </div>
                  );
                })}
            </div>
          </div>
        )}

        <div className="actions-bar">
          <button onClick={handleClear} className="clear-btn">
            Clear All
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
