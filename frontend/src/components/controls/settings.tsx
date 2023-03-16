import { useState, useEffect, useContext } from 'preact/hooks'
import styles from './filter.css'
import { GraphContext } from '../context'



export const Settings = ({ children }) => {
    return (
        <div className="fixed top-0 right-0 p-2 overflow-scroll h-screen bg-black bg-opacity-20">
            {children}
        </div>
    );
}
