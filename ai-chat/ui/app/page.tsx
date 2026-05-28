"use client";

import { useChat } from "ai/react";
import { useRef, useState, DragEvent, ChangeEvent } from "react";
import { Send, Paperclip, X, FileText, Image as ImageIcon, Loader2 } from "lucide-react";

export default function Chat() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: "http://localhost:8000/api/chat",
  });

  const [files, setFiles] = useState<File[]>([]);
  const [filePreviews, setFilePreviews] = useState<{ name: string; type: string; base64: string }[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const processFiles = async (selectedFiles: FileList | File[]) => {
    const validTypes = ["application/pdf", "image/png", "image/jpeg", "text/plain"];
    const newFiles = Array.from(selectedFiles).filter((file) =>
      validTypes.includes(file.type)
    );

    for (const file of newFiles) {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result as string;
        setFilePreviews((prev) => [
          ...prev,
          { name: file.name, type: file.type, base64: base64String },
        ]);
      };
      reader.readAsDataURL(file);
    }
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) {
      processFiles(e.dataTransfer.files);
    }
  };

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      processFiles(e.target.files);
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setFilePreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const onSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    // Create a custom event to pass files along with the message
    // In a real app, you might use experimental_attachments or a custom payload
    // Here we append the base64 files to the options in handleSubmit
    
    // Actually, Vercel AI SDK 3/6 handles attachments via options if configured,
    // or we can just embed them in the message body if custom API is used.
    // For simplicity, we'll pass it in body.
    handleSubmit(e, {
      body: {
        attachments: filePreviews,
      },
    });

    setFiles([]);
    setFilePreviews([]);
    
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  };

  return (
    <div className="flex flex-col h-screen bg-neutral-950 text-neutral-100 font-sans selection:bg-indigo-500/30">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-neutral-900/50 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <div className="w-3 h-3 bg-white rounded-full animate-pulse" />
          </div>
          <div>
            <h1 className="text-lg font-semibold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">
              EvalPlatform
            </h1>
            <p className="text-xs text-neutral-400 font-medium tracking-wide">MULTIMODAL RAG AGENT</p>
          </div>
        </div>
      </header>

      {/* Messages Area */}
      <main className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center opacity-0 animate-[fadeIn_0.5s_ease-out_forwards]">
            <div className="w-20 h-20 mb-6 rounded-2xl bg-gradient-to-tr from-indigo-500/20 to-purple-500/20 flex items-center justify-center border border-indigo-500/20">
              <ImageIcon className="w-10 h-10 text-indigo-400 opacity-80" />
            </div>
            <h2 className="text-2xl font-bold mb-3 text-neutral-200">How can I help you today?</h2>
            <p className="text-neutral-400 max-w-sm leading-relaxed">
              Upload PDFs, images, or text files, and ask questions. I'll search through them and provide grounded answers.
            </p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex flex-col max-w-3xl mx-auto ${
              message.role === "user" ? "items-end" : "items-start"
            }`}
          >
            <div
              className={`px-5 py-3.5 rounded-3xl max-w-[85%] shadow-sm ${
                message.role === "user"
                  ? "bg-gradient-to-br from-indigo-600 to-purple-600 text-white rounded-tr-sm"
                  : "bg-neutral-900 border border-white/5 text-neutral-200 rounded-tl-sm shadow-black/20"
              }`}
            >
              <div className="prose prose-invert max-w-none text-[15px] leading-relaxed">
                {message.content}
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex max-w-3xl mx-auto items-start">
            <div className="px-5 py-4 rounded-3xl rounded-tl-sm bg-neutral-900 border border-white/5 flex items-center gap-3">
              <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
              <span className="text-sm text-neutral-400 font-medium">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Input Area */}
      <div className="p-6 bg-gradient-to-t from-neutral-950 via-neutral-950 to-transparent">
        <div className="max-w-3xl mx-auto">
          {filePreviews.length > 0 && (
            <div className="flex flex-wrap gap-3 mb-4 p-3 bg-neutral-900/50 rounded-2xl border border-white/5 backdrop-blur-md">
              {filePreviews.map((preview, index) => (
                <div
                  key={index}
                  className="relative group flex items-center gap-3 bg-neutral-800 px-3 py-2 rounded-xl border border-white/10 overflow-hidden transition-all hover:border-indigo-500/50"
                >
                  {preview.type.startsWith("image/") ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={preview.base64}
                      alt={preview.name}
                      className="w-10 h-10 object-cover rounded-lg shadow-sm"
                    />
                  ) : (
                    <div className="w-10 h-10 flex items-center justify-center bg-indigo-500/10 text-indigo-400 rounded-lg">
                      <FileText className="w-5 h-5" />
                    </div>
                  )}
                  <div className="flex flex-col pr-6">
                    <span className="text-xs font-medium text-neutral-200 truncate max-w-[120px]">
                      {preview.name}
                    </span>
                    <span className="text-[10px] text-neutral-500 uppercase tracking-wider">
                      {preview.type.split("/")[1] || "File"}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeFile(index)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 bg-black/40 text-neutral-300 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500/80 hover:text-white"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <form
            onSubmit={onSubmit}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`relative flex items-end gap-2 bg-neutral-900 p-2 rounded-3xl border transition-colors duration-300 shadow-xl shadow-black/40 ${
              isDragging
                ? "border-indigo-500 bg-indigo-500/5"
                : "border-white/10 focus-within:border-indigo-500/50"
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              multiple
              accept=".pdf,.png,.jpg,.jpeg,.txt"
              className="hidden"
            />
            
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-3.5 text-neutral-400 hover:text-indigo-400 hover:bg-white/5 rounded-full transition-all active:scale-95"
              title="Attach files (PDF, PNG, JPG, TXT)"
            >
              <Paperclip className="w-5 h-5" />
            </button>

            <textarea
              value={input}
              onChange={handleInputChange}
              placeholder="Ask anything or drop files here..."
              className="w-full bg-transparent text-neutral-100 placeholder:text-neutral-500 outline-none resize-none py-3.5 max-h-32 min-h-[52px] text-[15px]"
              rows={1}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (input.trim() || files.length > 0) {
                    e.currentTarget.form?.requestSubmit();
                  }
                }
              }}
            />

            <button
              type="submit"
              disabled={isLoading || (!input.trim() && files.length === 0)}
              className="p-3.5 m-0.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-full transition-all disabled:opacity-50 disabled:hover:bg-indigo-600 active:scale-95 shadow-md shadow-indigo-500/20"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
          <div className="mt-3 text-center">
            <span className="text-[11px] text-neutral-500 font-medium tracking-wide">
              Supports PDF, PNG, JPG, TXT
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
