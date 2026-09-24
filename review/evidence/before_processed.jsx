function GeneratedPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4 sm:p-6">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-gray-200 p-6 sm:p-8 flex flex-col">
        <div className="w-full mb-4">
          <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight text-center mb-6">Login to your account</h1>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 w-full mb-4">
          <div className="flex-1 min-w-[120px]">
            <input type="text" placeholder="Enter email Your" className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-gray-800 focus:ring-2 focus:ring-blue-500 focus:outline-none shadow-sm" />
          </div>
          <div className="flex-1 min-w-[120px]">
            <input type="text" placeholder="Enter text..." className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-gray-800 focus:ring-2 focus:ring-blue-500 focus:outline-none shadow-sm" />
          </div>
        </div>
        <div className="w-full mb-4">
          <input type="password" placeholder="Enter your password" className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-gray-800 focus:ring-2 focus:ring-blue-500 focus:outline-none shadow-sm" />
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 w-full mb-4">
          <div className="flex-1 min-w-[120px]">
            <h2 className="text-base font-semibold text-gray-700 text-center mb-4">Subheading</h2>
          </div>
          <div className="flex-1 min-w-[120px]">
            <label className="inline-flex items-center gap-2 cursor-pointer"><span className="text-sm text-gray-700 font-medium">Remember me</span><input type="checkbox" className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500" /></label>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 w-full mb-4">
          <div className="flex-1 min-w-[120px]">
            <input type="text" placeholder="Enter text..." className="w-full border border-gray-300 rounded-lg px-3.5 py-2.5 text-gray-800 focus:ring-2 focus:ring-blue-500 focus:outline-none shadow-sm" />
          </div>
          <div className="flex-1 min-w-[120px]">
            <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg shadow transition-colors text-center">Login</button>
          </div>
        </div>
        <div className="w-full mb-4">
          <h2 className="text-base font-semibold text-gray-700 text-center mb-4">Don&#x27;t have an account? Sign_up</h2>
        </div>
      </div>
    </div>
  );
}

export default GeneratedPage;