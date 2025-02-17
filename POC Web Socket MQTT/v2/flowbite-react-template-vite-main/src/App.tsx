// import React, { useState, useEffect } from 'react';
// import { DarkThemeToggle } from "flowbite-react";

// const App = () => {
//   const [activeTab, setActiveTab] = useState("tab1");
//   const [messages, setMessages] = useState<string[]>([]);
//   const [input, setInput] = useState('');
//   const [allUsers, setAllUsers] = useState(null);
//   const [onlineUsers, setOnlineUsers] = useState(null);
//   const [offlineUsers, setOfflineUsers] = useState(null);
//   const [stationStatus, setStationStatus] = useState(null);
  

// const [socket, setSocket] = useState<WebSocket | null>(null);
// const [lastUpdated, setLastUpdated] = useState<number | null>(null);  // Added to track last update time
// const [totalUpdates, setTotalUpdates] = useState(0);  // Added to track total number of updates

//   // Establish WebSocket connection on component mount
//   useEffect(() => {
//     const ws = new WebSocket('wss://localhost:7158/ws'); // Make sure this matches your backend URL

//     ws.onopen = () => {
//       console.log('WebSocket connection established!');
//     };

//     ws.onmessage = (event) => {
//       const data = JSON.parse(event.data);
//       setAllUsers(data.allUsers ?? null);
//       setOnlineUsers(data.onlineUsers ?? null);
//       setOfflineUsers(data.offlineUsers ?? null);
//       setStationStatus(data.stationStatus ?? null);
//       console.log('Message from server:', event.data);
//       setLastUpdated(Date.now());  // Update timestamp on new data
//       setTotalUpdates(prev => prev + 1);  // Increment update count
//       setMessages((prevMessages) => [...prevMessages, event.data]);
//     };

//     ws.onerror = (error) => {
//       console.error('WebSocket error:', error);
//     };

//     ws.onclose = () => {
//       console.log('WebSocket connection closed.');
//     };

//     setSocket(ws);

//     return () => {
//       ws.close(); // Cleanup on unmount
//     };
//   }, []);

//   // Send message to WebSocket server
//   const sendMessage = () => {
//     if (socket && socket.readyState === WebSocket.OPEN) {
//       socket.send(input);
//       setInput('');
//     } else {
//       console.error('WebSocket is not open.');
//     }
//   };

//   return (
//     <main className="flex min-h-screen items-center justify-center gap-2 dark:bg-gray-800">
//       <div className="bg-white dark:bg-gray-900 shadow-lg rounded-2xl w-full max-w-md p-4">
//         <h1 className="text-2xl font-bold mb-4 text-center dark:text-white">Flowbite React + WebSocket</h1>

//         {/* Tabs List */}
//         <div className="flex space-x-2 border-b mb-4">
//           {['tab1', 'tab2', 'tab3', 'tab4'].map((tab, index) => (
//             <button
//               key={tab}
//               className={`px-4 py-2 rounded-t-md ${
//                 activeTab === tab
//                   ? "bg-blue-500 text-white"
//                   : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-white"
//               }`}
//               onClick={() => setActiveTab(tab)}
//             >
//               Tab {index + 1}
//             </button>
//           ))}
//         </div>

//         {/* Tabs Content */}
//         <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-b-lg shadow-inner">
//           {activeTab === "tab1" && (
//             <div>
//   <div>
//     <p><strong>Station All Users:</strong> {allUsers !== null ? allUsers : 'No data found'}</p>
//     <p><strong>Online Users:</strong> {onlineUsers !== null ? onlineUsers : 'No data found'}</p>
//     <p><strong>Offline Users:</strong> {offlineUsers !== null ? offlineUsers : 'No data found'}</p>
//     <p><strong>Station Status:</strong> {stationStatus !== null ? stationStatus : 'No data found'}</p>
//     <div className="bg-gray-200 dark:bg-gray-700 p-2 rounded">
//                   Last Updated: {lastUpdated ? `${Math.floor((Date.now() - lastUpdated) / 1000)} seconds ago` : 'No data found'}
//                 </div>
//                 <div className="bg-gray-200 dark:bg-gray-700 p-2 rounded">
//                   Total Updates: {totalUpdates}
//                 </div>
//   </div>

//               <h2 className="text-lg font-semibold mb-2">WebSocket Messages:</h2>
//               <div className="space-y-2">
//                 {messages.map((msg, idx) => (
//                   <div key={idx} className="bg-gray-200 dark:bg-gray-700 p-2 rounded">
//                     {msg}
//                   </div>
//                 ))}
//               </div>
//             </div>
//           )}
//           {activeTab === "tab2" && <div>Content for Tab 2</div>}
//           {activeTab === "tab3" && <div>Content for Tab 3</div>}
//           {activeTab === "tab4" && <div>Content for Tab 4</div>}
//         </div>

//         {/* Input and Send Button */}
//         <div className="mt-4">
//           <input
//             type="text"
//             value={input}
//             onChange={(e) => setInput(e.target.value)}
//             className="border p-2 w-full rounded mb-2 dark:bg-gray-700 dark:text-white"
//             placeholder="Enter message to send"
//           />
//           <button
//             onClick={sendMessage}
//             className="bg-green-500 text-white px-4 py-2 rounded w-full"
//           >
//             Send Message
//           </button>
//         </div>

//         {/* Dark Theme Toggle */}
//         <div className="flex justify-center mt-4">
//           <DarkThemeToggle />
//         </div>
//       </div>
//     </main>
//   );
// };

// export default App;

//TBD

import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import { DarkThemeToggle } from "flowbite-react";
import axios from 'axios'; // Optional, if using axios
// New page for Stations
const StationsPage = () => {
  const [stations, setStations] = useState<any[]>([]); // Store station data
  const [loading, setLoading] = useState<boolean>(true); // Track loading state
  const [error, setError] = useState<string>(''); // Track error state

  useEffect(() => {
    // Fetch station data when the component mounts
    axios.get('https://localhost:7158/api/Station')
      .then((response) => {
        setStations(response.data); // Set data into state
        setLoading(false); // Set loading to false once data is fetched
      })
      .catch((error) => {
        setError('Failed to fetch stations');
        setLoading(false); // Set loading to false in case of error
      });
  }, []);

  // Render the stations data in a table
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-gray-100 dark:bg-gray-800">
      <div className="bg-white dark:bg-gray-900 shadow-lg rounded-xl w-full max-w-4xl p-6">
        <h1 className="text-3xl font-bold text-center text-gray-800 dark:text-white mb-6">Stations</h1>

        {/* Loading and Error States */}
        {loading && (
          <div className="flex justify-center items-center space-x-2">
            <div className="spinner-border animate-spin inline-block w-8 h-8 border-4 border-blue-500 rounded-full" role="status">
              <span className="sr-only">Loading...</span>
            </div>
            <span className="text-gray-700 dark:text-white">Loading stations...</span>
          </div>
        )}

        {error && !loading && (
          <div className="bg-red-500 text-white p-4 rounded-lg text-center">
            {error}
          </div>
        )}

        {/* Stations Table */}
        {!loading && !error && (
          <div className="overflow-x-auto">
            <table className="min-w-full table-auto bg-white dark:bg-gray-900 shadow-lg rounded-lg">
              <thead>
                <tr>
                  <th className="px-4 py-2 text-left font-semibold text-gray-600 dark:text-white">ID</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-600 dark:text-white">Name</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-600 dark:text-white">Location</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-600 dark:text-white">Status</th>
                </tr>
              </thead>
              <tbody>
                {stations.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center text-gray-500 dark:text-white py-4">No stations available</td>
                  </tr>
                ) : (
                  stations.map((station) => (
                    <tr key={station.id} className="border-b dark:border-gray-700">
                      <td className="px-4 py-2 text-gray-800 dark:text-white">{station.id}</td>
                      <td className="px-4 py-2 text-gray-800 dark:text-white">{station.name}</td>
                      <td className="px-4 py-2 text-gray-800 dark:text-white">{station.location}</td>
                      <td className="px-4 py-2 text-gray-800 dark:text-white">{station.status}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};


const App = () => {
  const [activeTab, setActiveTab] = useState("tab1");
  const [messages, setMessages] = useState<string[]>([]);
  const [input, setInput] = useState('');
  const [allUsers, setAllUsers] = useState(null);
  const [onlineUsers, setOnlineUsers] = useState(null);
  const [offlineUsers, setOfflineUsers] = useState(null);
  const [stationStatus, setStationStatus] = useState(null);

  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);  // Added to track last update time
  const [totalUpdates, setTotalUpdates] = useState(0);  // Added to track total number of updates

  // Establish WebSocket connection on component mount
  useEffect(() => {
    const ws = new WebSocket('wss://localhost:7158/ws'); // Make sure this matches your backend URL

    ws.onopen = () => {
      console.log('WebSocket connection established!');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setAllUsers(data.allUsers ?? null);
      setOnlineUsers(data.onlineUsers ?? null);
      setOfflineUsers(data.offlineUsers ?? null);
      setStationStatus(data.stationStatus ?? null);
      console.log('Message from server:', event.data);
      setLastUpdated(Date.now());  // Update timestamp on new data
      setTotalUpdates(prev => prev + 1);  // Increment update count
      setMessages((prevMessages) => [...prevMessages, event.data]);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('WebSocket connection closed.');
    };

    setSocket(ws);

    return () => {
      ws.close(); // Cleanup on unmount
    };
  }, []);

  // Send message to WebSocket server
  const sendMessage = () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(input);
      setInput('');
    } else {
      console.error('WebSocket is not open.');
    }
  };

  return (
    <Router>
      <main className="flex min-h-screen items-center justify-center gap-2 dark:bg-gray-800">
        <div className="bg-white dark:bg-gray-900 shadow-lg rounded-2xl w-full max-w-md p-4">
          <h1 className="text-2xl font-bold mb-4 text-center dark:text-white">Flowbite React + WebSocket</h1>

          {/* Tabs List */}
          <div className="flex space-x-2 border-b mb-4">
            {['tab1', 'tab2', 'tab3', 'tab4'].map((tab, index) => (
              <button
                key={tab}
                className={`px-4 py-2 rounded-t-md ${
                  activeTab === tab
                    ? "bg-blue-500 text-white"
                    : "bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-white"
                }`}
                onClick={() => setActiveTab(tab)}
              >
                Tab {index + 1}
              </button>
            ))}
            <Link to="/stations">
              <button className="px-4 py-2 rounded-t-md bg-blue-500 text-white">
                View Stations
              </button>
            </Link>
          </div>

          {/* Routing for Tabs and Pages */}
          <div className="p-4 bg-gray-100 dark:bg-gray-800 rounded-b-lg shadow-inner">
            <Routes>
              <Route path="/stations" element={<StationsPage />} />
              <Route
                path="/"
                element={
                  <div>
                    {activeTab === "tab1" && (
                      <div>
                        <div>
                          <p><strong>Station All Users:</strong> {allUsers !== null ? allUsers : 'No data found'}</p>
                          <p><strong>Online Users:</strong> {onlineUsers !== null ? onlineUsers : 'No data found'}</p>
                          <p><strong>Offline Users:</strong> {offlineUsers !== null ? offlineUsers : 'No data found'}</p>
                          <p><strong>Station Status:</strong> {stationStatus !== null ? stationStatus : 'No data found'}</p>
                          <div className="bg-gray-200 dark:bg-gray-700 p-2 rounded">
                            Last Updated: {lastUpdated ? `${Math.floor((Date.now() - lastUpdated) / 1000)} seconds ago` : 'No data found'}
                          </div>
                          <div className="bg-gray-200 dark:bg-gray-700 p-2 rounded">
                            Total Updates: {totalUpdates}
                          </div>
                        </div>
                        <h2 className="text-lg font-semibold mb-2">WebSocket Messages:</h2>
                        <div className="space-y-2">
                          {messages.map((msg, idx) => (
                            <div key={idx} className="bg-gray-200 dark:bg-gray-700 p-2 rounded">
                              {msg}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                }
              />
            </Routes>
          </div>

          {/* Input and Send Button */}
          <div className="mt-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="border p-2 w-full rounded mb-2 dark:bg-gray-700 dark:text-white"
              placeholder="Enter message to send"
            />
            <button
              onClick={sendMessage}
              className="bg-green-500 text-white px-4 py-2 rounded w-full"
            >
              Send Message
            </button>
          </div>

          {/* Dark Theme Toggle */}
          <div className="flex justify-center mt-4">
            <DarkThemeToggle />
          </div>
        </div>
      </main>
    </Router>
  );
};

export default App;
