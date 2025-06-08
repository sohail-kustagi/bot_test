import React, { useEffect, useState } from 'react';
import endPoints from '../app/api';
import TitleHead from './TitleHead';

const DATA_KEYS = [
    { name: "Account Num.", key: "Id", fixed: -1 },
    { name: "Balance", key: "Balance", fixed: -1 },
    { name: "NAV", key: "Equity", fixed: -1 },
    { name: "Open Trades", key: "OpenTrades", fixed: -1 },
    { name: "Unrealized PL", key: "Profit", fixed: -1 },
    { name: "Closeout %", key: "MarginCallLevel", fixed: -1 },
    { name: "Last Trans. ID", key: "LastTransactionID", fixed: -1 },
];

function AccountSummary() {

    const [account, setAccount] = useState(null);

    useEffect(() => {
        loadAccount();
        const interval = setInterval(() => {
            loadAccount();
        }, 5000); // Fetch data every 5 seconds
        return () => clearInterval(interval); // Cleanup on unmount
    }, [])

    const loadAccount = async () => {
        const data = await endPoints.account();
        setAccount(data);
    }

    return (
        <div>
            <TitleHead title="Account Summary" />
            {
                account && <div className='segment'>
                    {
                        DATA_KEYS.map(item => {
                            return <div key={item.key} className="account-row">
                                <div className='bold header'>{item.name}</div>
                                <div>{account[item.key]}</div>
                            </div>
                        })
                    }
                </div>
            }
        </div>
    )
}

export default AccountSummary