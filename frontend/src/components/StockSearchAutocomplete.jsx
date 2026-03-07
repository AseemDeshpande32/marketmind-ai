import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiSearch } from 'react-icons/fi';
import { searchScripCode } from '../services/market5paisaService';
import './StockSearchAutocomplete.css';

const StockSearchAutocomplete = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchRef = useRef(null);
  const debounceTimer = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search function
  const handleSearch = async (query) => {
    if (query.trim().length < 2) {
      setSuggestions([]);
      setShowDropdown(false);
      return;
    }

    setIsLoading(true);
    try {
      const results = await searchScripCode(query);
      if (results && results.length > 0) {
        // Limit to top 10 results
        setSuggestions(results.slice(0, 10));
        setShowDropdown(true);
      } else {
        setSuggestions([]);
        setShowDropdown(false);
      }
    } catch (error) {
      console.error('Search error:', error);
      setSuggestions([]);
      setShowDropdown(false);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle input change with debouncing
  const handleInputChange = (e) => {
    const value = e.target.value;
    setSearchQuery(value);

    // Clear previous timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    // Set new timer for debounced search
    debounceTimer.current = setTimeout(() => {
      handleSearch(value);
    }, 300); // 300ms delay
  };

  // Handle stock selection
  const handleStockSelect = (stock) => {
    setSearchQuery('');
    setSuggestions([]);
    setShowDropdown(false);
    navigate(`/stock/${stock.name}`);
  };

  // Handle Enter key press
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && searchQuery.trim()) {
      if (suggestions.length > 0) {
        handleStockSelect(suggestions[0]);
      }
    }
  };

  return (
    <div className="stock-search-autocomplete" ref={searchRef}>
      <div className="search-input-wrapper">
        <FiSearch className="search-icon" />
        <input
          type="text"
          className="search-input"
          placeholder="Search stocks (e.g., Reliance, TCS, TATA...)"
          value={searchQuery}
          onChange={handleInputChange}
          onKeyPress={handleKeyPress}
          onFocus={() => {
            if (suggestions.length > 0) {
              setShowDropdown(true);
            }
          }}
        />
        {isLoading && <div className="search-loader"></div>}
      </div>

      {showDropdown && suggestions.length > 0 && (
        <div className="suggestions-dropdown">
          <div className="suggestions-header">
            Found {suggestions.length} stock{suggestions.length !== 1 ? 's' : ''}
          </div>
          <div className="suggestions-list">
            {suggestions.map((stock, index) => (
              <div
                key={`${stock.exchange}-${stock.scripCode}-${index}`}
                className="suggestion-item"
                onClick={() => handleStockSelect(stock)}
              >
                <div className="suggestion-main">
                  <span className="suggestion-name">{stock.name}</span>
                  <span className="suggestion-exchange">{stock.exchange}</span>
                </div>
                <div className="suggestion-fullname">{stock.fullName}</div>
                <div className="suggestion-code">Code: {stock.scripCode}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {showDropdown && searchQuery.trim().length >= 2 && suggestions.length === 0 && !isLoading && (
        <div className="suggestions-dropdown">
          <div className="no-results">
            No stocks found for "{searchQuery}"
          </div>
        </div>
      )}
    </div>
  );
};

export default StockSearchAutocomplete;
