import React, { useState } from 'react';
import './Demo.css';

function Demo() {
  const [prompt, setPrompt] = useState('');
  const [file, setFile] = useState(null);
  const [fileInfo, setFileInfo] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      const sizeKB = (selectedFile.size / 1024).toFixed(2);
      const format = selectedFile.name.endsWith('.toon') ? 'TOON' : 'JSON';
      setFileInfo(`${format} file: ${selectedFile.name} (${sizeKB} KB)`);
    } else {
      setFile(null);
      setFileInfo('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select a file');
      return;
    }

    if (!prompt.trim()) {
      setError('Please enter a prompt');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('prompt', prompt);

      const response = await fetch('/api/analyze', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (response.ok && data.success) {
        setResult(data);
      } else {
        setError(data.error || 'An error occurred');
      }
    } catch (err) {
      setError(`Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="demo-wrapper">
      <div className="demo-container">
      <h1>📊 File Analyzer</h1>
      <p className="subtitle">Upload a JSON or TOON file and ask questions using AWS Bedrock</p>
      
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="prompt">Your Question / Prompt:</label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows="3"
            placeholder="e.g., Which servers serve the maximum amount of traffic?"
            required
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="file">Upload File (JSON or TOON):</label>
          <input
            type="file"
            id="file"
            accept=".json,.toon"
            onChange={handleFileChange}
            required
          />
          {fileInfo && (
            <div className="file-info">
              {fileInfo}
              <span className={`format-badge ${file?.name.endsWith('.toon') ? 'toon' : 'json'}`}>
                {file?.name.endsWith('.toon') ? 'TOON' : 'JSON'}
              </span>
            </div>
          )}
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Analyzing...' : 'Analyze File'}
        </button>
      </form>
      
      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Analyzing file with AWS Bedrock...</p>
        </div>
      )}
      
      {error && (
        <div className="result error">
          <h3>❌ Error</h3>
          <pre>{error}</pre>
          {(error.includes('token') || error.includes('too large')) && (
            <p style={{ marginTop: '10px' }}>
              <strong>💡 Tip:</strong> Try using a TOON file instead of JSON - it uses fewer tokens!
            </p>
          )}
        </div>
      )}
      
      {result && (
        <div className="result success">
          <h3>✅ Analysis Complete</h3>
          <div className="token-info">
            Estimated tokens: {result.estimated_tokens?.toLocaleString() || 'N/A'} | 
            Format: <span className={`format-badge ${result.file_format}`}>{result.file_format?.toUpperCase()}</span> | 
            Items: {result.item_count || 'N/A'}
          </div>
          <pre>{result.response || 'No response'}</pre>
        </div>
      )}
      </div>
    </div>
  );
}

export default Demo;
