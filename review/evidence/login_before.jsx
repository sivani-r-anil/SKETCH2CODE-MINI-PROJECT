function GeneratedPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8 flex flex-col">
        <div className="w-full mb-4">
          <div className="text-gray-700 text-center">LOGIN</div>
        </div>
        <div className="w-full mb-4">
          <label className="text-sm font-semibold text-gray-700 block mb-1">Emall</label>
        </div>
        <div className="w-full mb-4">
          <input type="text" placeholder="Enter text..." className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-gray-800 focus:ring-2 focus:ring-blue-500 focus:outline-none shadow-sm" />
        </div>
        <div className="w-full mb-4">
          <input type="text" placeholder="Enter text..." className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-gray-800 focus:ring-2 focus:ring-blue-500 focus:outline-none shadow-sm" />
        </div>
        <div className="w-full mb-4">
          <label className="inline-flex items-center gap-2 cursor-pointer"><span className="text-sm text-gray-700 font-medium">Renambet</span><input type="checkbox" className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500" /></label>
        </div>
        <div className="w-full mb-4">
          <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg shadow transition-colors text-center">SUBMIT</button>
        </div>
        <div className="w-full mb-4">
          <label className="text-sm font-semibold text-gray-700 block mb-1">Create account</label>
        </div>
      </div>
    </div>
  );
}

export default GeneratedPage;