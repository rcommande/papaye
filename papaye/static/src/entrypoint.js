import ReactDOM from 'react-dom';
import React from 'react';
import { Provider } from 'react-redux';
import { createStore } from 'redux';
import { BrowserRouter } from 'react-router-dom';
import { Map } from 'immutable';

window.Map = Map;

import Main from './index.js';
import appReducer from './reducers';

const store = createStore(
    appReducer,
    window.Map(window.INITIAL_STATE),
    window.__REDUX_DEVTOOLS_EXTENSION__ && window.__REDUX_DEVTOOLS_EXTENSION__()
);

ReactDOM.hydrate(
    <BrowserRouter>
        <Provider store={store}>
            <Main/>
        </Provider>
    </BrowserRouter>,
    document.getElementById('root'));

export default Main;