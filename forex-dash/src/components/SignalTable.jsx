import React, { useEffect, useState } from 'react';

function SignalTable() {
    const [signals, setSignals] = useState([]);

    useEffect(() => {
        // Fetch the last 10 signals from the backend
        const fetchSignals = async () => {
            try {
                const response = await fetch('http://localhost:5000/api/signals'); // Updated to use full backend URL
                if (response.ok) {
                    const data = await response.json();
                    console.log('Fetched signals:', data); // Debugging log
                    setSignals(data);
                } else {
                    console.error('Failed to fetch signals:', response.statusText);
                }
            } catch (error) {
                console.error('Error fetching signals:', error);
            }
        };

        fetchSignals();

        // Optional: Poll for updates every 5 seconds
        const interval = setInterval(fetchSignals, 5000);
        return () => clearInterval(interval);
    }, []);

    console.log('SignalTable rendered'); // Debugging log to confirm rendering

    return (
        <div className="signal-table-container">
            <h2>Last 10 Signals</h2>
            <table className="signal-table">
                <thead>
                    <tr>
                        <th>PAIR</th>
                        <th>Time</th>
                        <th>Mid Close</th>
                        <th>Mid Open</th>
                        <th>SL</th>
                        <th>TP</th>
                        <th>Spread</th>
                        <th>Gain</th>
                        <th>Loss</th>
                        <th>Signal</th>
                    </tr>
                </thead>
                <tbody>
                    {signals.length > 0 ? (
                        signals.map((signal, index) => (
                            <tr key={index}>
                                <td>{signal.PAIR}</td>
                                <td>{new Date(signal.time).toLocaleString()}</td>
                                <td>{signal.mid_c}</td>
                                <td>{signal.mid_o}</td>
                                <td>{signal.SL}</td>
                                <td>{signal.TP}</td>
                                <td>{signal.SPREAD}</td>
                                <td>{signal.GAIN}</td>
                                <td>{signal.LOSS}</td>
                                <td>{signal.SIGNAL}</td>
                            </tr>
                        ))
                    ) : (
                        <tr>
                            <td colSpan="10">No signals available</td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    );
}

export default SignalTable;